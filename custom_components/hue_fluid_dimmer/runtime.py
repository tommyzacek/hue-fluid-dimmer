"""Bridge-wide polling, public Hue wake events, and opt-in controller actions."""

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr

from .api import BridgeClient, BridgeError
from .const import (
    CONF_BINDINGS,
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
from .models import ReportTracker

_LOGGER = logging.getLogger(__name__)


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
        if data.get("type") != "short_release":
            return
        for item in self.resources:
            device = self.device(item.get("owner", {}).get("rid", ""))
            if device and device.id == data.get("device_id"):
                binding = self.entry.options.get(CONF_BINDINGS, {}).get(item["id"], {})
                if binding.get("enabled") and binding.get(f"button_{data.get('subtype')}"):
                    self.create_task(self.button(item["id"], binding, data["subtype"]))
                return

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
                    binding = self.entry.options.get(CONF_BINDINGS, {}).get(report.resource_id, {})
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

    async def button(self, resource_id: str, binding: dict, index: int) -> None:
        async with self.button_locks.setdefault(resource_id, asyncio.Lock()):
            entity_id = binding[f"button_{index}"]
            domain = entity_id.split(".", 1)[0]
            service = "toggle" if domain == "light" else "turn_on"
            if domain not in ("light", "scene", "script"):
                return
            # Cancel the pending ramp before a button switches a light or scene.
            await self.dimmer.cancel_targets(tuple(binding.get("lights", [])))
            await self.hass.services.async_call(
                domain, service, {"entity_id": entity_id}, blocking=True
            )

    async def close(self) -> None:
        self.closed = True
        if self.unsubscribe:
            self.unsubscribe()
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        await self.dimmer.close()
