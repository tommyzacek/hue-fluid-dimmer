"""Bridge-wide polling, public Hue wake events, and opt-in controller actions."""

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr

from .api import BridgeClient, BridgeError
from .bindings import button_actions, targets
from .configuration import controller_binding
from .const import (
    CONF_HUE_ENTRY,
    CONF_INTERVAL,
    CONF_MODE,
    CONF_WINDOW,
    DEFAULT_INTERVAL,
    DEFAULT_WINDOW,
    EVENT_ROTATION,
    HUE_DOMAIN,
    MODE_ACTIVE,
    MODE_CONTINUOUS,
)
from .control import Dimmer
from .gestures import CLICK_WINDOW, Gestures
from .models import ReportTracker

_LOGGER = logging.getLogger(__name__)
QUIET_EPSILON = 0.001


class Runtime:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass, self.entry = hass, entry
        self.resources: list[dict[str, Any]] = []
        self.tracker = ReportTracker()
        self.available = True
        self.poll_count = self.error_count = self.report_count = 0
        self.wake = asyncio.Event()
        self.active_until = 0.0
        self.closed = False
        self.task: asyncio.Task | None = None
        self.unsubscribe: Callable[[], None] | None = None
        self.client = BridgeClient(
            aiohttp_client.async_get_clientsession(hass, verify_ssl=False),
            self.credentials,
        )
        self.dimmer = Dimmer(self.read_brightness, self.send_brightness, self.create_task)
        self.button_locks: dict[str, asyncio.Lock] = {}
        self.button_task: asyncio.Task | None = None
        self.action_tasks: set[asyncio.Task] = set()
        self.button_map: dict[str, tuple[str, int]] = {}
        self.button_poll_task: asyncio.Task | None = None
        self.button_wake = asyncio.Event()
        self.button_active_until = 0.0
        self.button_poll_count = self.button_error_count = 0
        self.button_baselined = False
        # REST can advance complete adjacent transitions. A gap blocks it until SSE catches up.
        self.button_snapshots: dict[tuple[str, int], tuple[float, str, float, float]] = {}
        self.button_gaps: dict[tuple[str, int], float] = {}
        self.gestures = Gestures(self.actions, self.emit_button, self.button_ready)

    def create_task(self, coro) -> asyncio.Task:
        return self.entry.async_create_background_task(
            self.hass, coro, "Hue Fluid Dimmer worker", eager_start=False
        )

    def credentials(self) -> tuple[str, str]:
        """Isolate the dependency on Hue's config-entry credential field names."""
        source = self.hass.config_entries.async_get_entry(self.entry.data[CONF_HUE_ENTRY])
        if source is None or source.state is not ConfigEntryState.LOADED:
            raise BridgeError("Selected Hue integration is not loaded")
        try:
            return source.data[CONF_HOST], source.data[CONF_API_KEY]
        except KeyError as err:
            raise BridgeError("Selected Hue entry has unsupported credentials") from err

    async def initialize(self) -> None:
        self.resources = await self.client.rotary_resources()
        self.tracker.baseline(self.resources)

    @callback
    def start(self) -> None:
        self.unsubscribe = self.hass.bus.async_listen("hue_event", self.on_hue_event)
        self.task = self.create_task(self.poll())
        self.button_task = self.create_task(self.listen_buttons())
        self.button_poll_task = self.create_task(self.poll_buttons())

    def device(self, owner_id: str):
        return dr.async_get(self.hass).async_get_device_by_identifier(
            (HUE_DOMAIN, owner_id), self.entry.data[CONF_HUE_ENTRY]
        )

    def controllers(self) -> dict[str, str]:
        return {
            item["id"]: (
                device.name_by_user or device.name or item["id"]
                if (device := self.device(item["owner"]["rid"]))
                else item["id"]
            )
            for item in self.resources
            if isinstance(item.get("id"), str) and item.get("owner", {}).get("rid")
        }

    @callback
    def on_hue_event(self, event: Event) -> None:
        data = event.data
        if data.get("unique_id") in self.controllers():
            # Native rotary events only wake polling: never apply their steps twice.
            self.active_until = time.monotonic() + self.entry.options.get(
                CONF_WINDOW, DEFAULT_WINDOW
            )
            self.wake.set()
            return
        # Timestamp-free public button events can wake polling, never execute actions.
        mapped = self.button_map.get(data.get("unique_id"))
        if mapped and self.actions(*mapped):
            self.wake_buttons()

    def actions(self, resource_id: str, index: int) -> dict:
        binding = controller_binding(self.entry, resource_id)
        return button_actions(binding, index) if binding.get("enabled") else {}

    def emit_button(self, resource_id: str, index: int, action: str) -> None:
        binding = controller_binding(self.entry, resource_id)
        if not binding.get("enabled") or not button_actions(binding, index).get(action):
            return
        task = self.create_task(self.button(resource_id, binding, index, action))
        self.action_tasks.add(task)
        task.add_done_callback(self.action_tasks.discard)

    def wake_buttons(self) -> None:
        self.button_active_until = time.monotonic() + self.entry.options.get(
            CONF_WINDOW, DEFAULT_WINDOW
        )
        self.button_wake.set()

    def map_buttons(self, buttons: list[dict]) -> None:
        owners = {item.get("owner", {}).get("rid"): item["id"] for item in self.resources}
        self.button_map = {
            item["id"]: (owners[item["owner"]["rid"]], item["metadata"]["control_id"])
            for item in buttons
            if isinstance(item, dict)
            and item.get("owner", {}).get("rid") in owners
            and item.get("metadata", {}).get("control_id") in (1, 2, 3, 4)
            and isinstance(item.get("id"), str)
        }

    @staticmethod
    def button_report(item: dict):
        feature = item.get("button")
        report = feature.get("button_report") if isinstance(feature, dict) else None
        if not isinstance(report, dict) or not isinstance(report.get("event"), str):
            return None
        try:
            updated = datetime.fromisoformat(report["updated"])
            if updated.tzinfo is not None:
                return updated.timestamp(), report["event"]
        except KeyError, TypeError, ValueError:
            pass
        return None

    def button_ready(self, key, state) -> bool:
        """Hold expiry if REST proves a newer transition is still awaiting SSE."""
        snapshot = self.button_snapshots.get(key)
        return snapshot is None or snapshot[0] <= self.gestures.latest.get(key, float("-inf"))

    def confirm_buttons(self) -> None:
        for key, state in list(self.gestures.pending.items()):
            snapshot = self.button_snapshots.get(key)
            if snapshot is None or state.pressed or not state.count:
                continue
            updated, event, first_seen, checked = snapshot
            if (
                event == "short_release"
                and updated == state.released
                and checked - first_seen >= CLICK_WINDOW
                and time.monotonic() - checked <= 0.5
            ):
                self.gestures.finish(key)

    def button_poll_delay(self, interval: float, started: float) -> float:
        """Align a fresh query with the earliest pending quiet-time deadline."""
        now = time.monotonic()
        delay = max(0, interval - (now - started))
        deadlines = []
        for key, state in self.gestures.pending.items():
            snapshot = self.button_snapshots.get(key)
            if (
                snapshot is not None
                and not state.pressed
                and state.count
                and snapshot[0] == state.released
                and snapshot[1] == "short_release"
            ):
                deadlines.append(snapshot[2] + CLICK_WINDOW + QUIET_EPSILON)
        if deadlines:
            delay = min(delay, max(0, min(deadlines) - now))
        return delay

    def consume_button_snapshots(
        self, buttons: list[dict], baseline: bool = False, checked_at: float | None = None
    ) -> None:
        now = time.monotonic()
        checked = now if checked_at is None else checked_at
        self.map_buttons(buttons)
        for item in buttons:
            key = self.button_map.get(item.get("id"))
            report = self.button_report(item)
            if key is None or report is None or not self.actions(*key):
                continue
            updated, event = report
            previous = self.button_snapshots.get(key)
            if previous and updated < previous[0]:
                continue
            first_seen = previous[2] if previous and previous[:2] == report else now
            self.button_snapshots[key] = (updated, event, first_seen, checked)
            if not baseline and (previous is None or updated > previous[0]):
                self.wake_buttons()
                if key in self.button_gaps:
                    self.button_gaps[key] = max(self.button_gaps[key], updated)
                else:
                    if event not in ("initial_press", "short_release") or not self.gestures.feed(
                        *key, event, updated
                    ):
                        self.button_gaps[key] = updated
        if not baseline:
            self.confirm_buttons()

    async def poll_buttons(self) -> None:
        interval = self.entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        continuous = self.entry.options.get(CONF_MODE, MODE_ACTIVE) == MODE_CONTINUOUS
        failures = 0
        while not self.closed:
            if (
                not continuous
                and time.monotonic() >= self.button_active_until
                and not self.gestures.pending
            ):
                self.button_wake.clear()
                await self.button_wake.wait()
                if self.closed:
                    return
            started = time.monotonic()
            try:
                buttons = await self.client.button_resources()
                self.button_poll_count += 1
                baseline = not self.button_baselined or bool(failures)
                self.consume_button_snapshots(buttons, baseline=baseline, checked_at=started)
                failures = 0
                self.button_baselined = True
                delay = self.button_poll_delay(interval, started)
            except BridgeError as err:
                self.button_error_count += 1
                failures += 1
                self.button_snapshots.clear()
                self.button_gaps.clear()
                self.button_baselined = False
                if failures == 1:
                    _LOGGER.warning("Hue button polling unavailable; backing off")
                delay = max(err.retry_after, min(30, 2 ** min(failures - 1, 5)))
            await asyncio.sleep(delay)

    def consume_buttons(self, envelopes: list[dict]) -> None:
        reports = []
        for envelope in envelopes:
            if not isinstance(envelope, dict) or envelope.get("type") != "update":
                continue
            items = envelope.get("data", [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or item.get("type") != "button":
                    continue
                mapped = self.button_map.get(item.get("id"))
                report = self.button_report(item)
                if mapped and report:
                    updated, event = report
                    reports.append((updated, mapped, event))
        # Process the entire frame before any expiry callback can run.
        for updated, (resource_id, index), event in sorted(reports):
            if self.actions(resource_id, index):
                self.wake_buttons()
            self.gestures.feed(resource_id, index, event, updated)
            gap = self.button_gaps.get((resource_id, index))
            if (
                gap is not None
                and self.gestures.latest.get((resource_id, index), float("-inf")) >= gap
            ):
                self.button_gaps.pop((resource_id, index), None)
        self.confirm_buttons()

    async def listen_buttons(self) -> None:
        failures = 0
        while not self.closed:
            try:
                buttons = await self.client.button_resources()
                if self.button_baselined:
                    self.map_buttons(buttons)
                else:
                    self.consume_button_snapshots(buttons, baseline=True)
                    self.button_baselined = True
                async for envelopes in self.client.button_events():
                    failures = 0
                    self.consume_buttons(envelopes)
            except BridgeError as err:
                failures += 1
                self.gestures.cancel()
                if failures == 1:
                    _LOGGER.warning("Hue button stream unavailable; reconnecting")
                await asyncio.sleep(max(err.retry_after, min(30, 2 ** min(failures - 1, 5))))

    async def poll(self) -> None:
        interval = self.entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        continuous = self.entry.options.get(CONF_MODE, MODE_ACTIVE) == MODE_CONTINUOUS
        failures = 0
        while not self.closed:
            if not continuous and time.monotonic() >= self.active_until:
                # No await between clear and checking the deadline: no lost wake-up.
                self.wake.clear()
                await self.wake.wait()
                if self.closed:
                    return
            started = time.monotonic()
            try:
                resources = await self.client.rotary_resources()
                self.poll_count += 1
                if failures:
                    # Do not execute old reports accumulated during an outage.
                    self.tracker.baseline(resources)
                    reports = []
                    _LOGGER.info("Hue rotary polling recovered")
                else:
                    reports = self.tracker.consume(resources)
                self.resources = resources
                self.available = True
                failures = 0
                for report in reports:
                    self.report_count += 1
                    self.active_until = time.monotonic() + self.entry.options.get(
                        CONF_WINDOW, DEFAULT_WINDOW
                    )
                    self.hass.bus.async_fire(EVENT_ROTATION, report.event_data())
                    binding = controller_binding(self.entry, report.resource_id)
                    self.dimmer.rotate(binding, report.signed_steps)
                delay = max(0, interval - (time.monotonic() - started))
            except BridgeError as err:
                self.error_count += 1
                self.available = False
                failures += 1
                if failures == 1:
                    _LOGGER.warning("Hue rotary polling unavailable; backing off")
                delay = max(err.retry_after, min(30, 2 ** min(failures - 1, 5)))
            await asyncio.sleep(delay)

    def read_brightness(self, lights: tuple[str, ...]) -> float | None:
        values = []
        for entity_id in lights:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                continue
            if state.state == "off":
                values.append(0.0)
            elif isinstance(state.attributes.get("brightness"), (float, int)):
                values.append(state.attributes["brightness"] / 255 * 100)
        return sum(values) / len(values) if values else None

    async def send_brightness(
        self, lights: tuple[str, ...], brightness: float, transition: float
    ) -> None:
        data = {"entity_id": list(lights), "transition": transition}
        if brightness > 0:
            data["brightness_pct"] = max(1, round(brightness))
        await self.hass.services.async_call(
            "light", "turn_on" if brightness > 0 else "turn_off", data, blocking=True
        )

    async def button(
        self, resource_id: str, binding: dict, index: int, action: str = "short"
    ) -> None:
        async with self.button_locks.setdefault(resource_id, asyncio.Lock()):
            selected = targets(button_actions(binding, index).get(action))
            if not selected:
                return
            domain = selected[0].split(".", 1)[0]
            service = "toggle" if domain == "light" else "turn_on"
            if domain not in ("light", "scene", "script"):
                return
            if any(item.split(".", 1)[0] != domain for item in selected):
                return
            if domain != "light" and len(selected) != 1:
                return
            # Cancel the pending ramp before a button switches a light or scene.
            await self.dimmer.cancel_targets(tuple(binding.get("lights", [])))
            await self.hass.services.async_call(
                domain,
                service,
                {"entity_id": selected if domain == "light" else selected[0]},
                blocking=True,
            )

    async def close(self) -> None:
        self.closed = True
        if self.unsubscribe:
            self.unsubscribe()
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        self.gestures.cancel()
        tasks = list(self.action_tasks)
        if self.button_task:
            tasks.append(self.button_task)
        if self.button_poll_task:
            tasks.append(self.button_poll_task)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.dimmer.close()
