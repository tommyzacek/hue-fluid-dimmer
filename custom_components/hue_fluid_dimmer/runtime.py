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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .adaptive import AdaptiveCooperation
from .api import BridgeClient, BridgeError
from .bindings import (
    button_actions,
    button_long_mode,
    button_operation,
    percentage_targets,
    targets,
)
from .configuration import controller_binding
from .const import (
    CONF_HUE_ENTRY,
    CONF_INTERVAL,
    CONF_MODE,
    CONF_WINDOW,
    DEFAULT_INTERVAL,
    DEFAULT_WINDOW,
    DOMAIN,
    EVENT_ROTATION,
    HUE_DOMAIN,
    MODE_ACTIVE,
    MODE_CONTINUOUS,
)
from .control import Dimmer
from .controller_models import HoldDirections, controller_kind, motion_service_role
from .dial_routing import DialRouting
from .gate import allows
from .gestures import CLICK_WINDOW, Gestures
from .models import ReportTracker
from .motion import MotionLighting
from .motion_bridge import request as motion_request
from .motion_targets import expand_targets, hue_group_members
from .percentage import PercentageRamp

_LOGGER = logging.getLogger(__name__)
QUIET_EPSILON = 0.001
RAMP_INITIAL_TRANSITION = 0.8
RAMP_MIN_TRANSITION = 0.2
RAMP_MAX_TRANSITION = 1.0
RAMP_DUPLICATE_REPEAT_WINDOW = 0.15
RAMP_STEP = 10.0


def kind(item):
    if any(s.get("rtype") == "motion" for s in item.get("services", [])):
        return "motion"
    return controller_kind(item.get("product_data", {}).get("model_id"))


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
        self.adaptive = AdaptiveCooperation(
            hass, lambda: self.entry.options.get("adaptive_lighting", False)
        )
        self.motion = MotionLighting(
            hass,
            self.create_task,
            self.adaptive,
            storage=Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.motion_levels")
            if hasattr(entry, "entry_id")
            else None,
        )
        self.motion.gate_options = lambda: self.entry.options
        self.motion.stop_ramps = self.stop_motion_ramps
        self.motion_unsubscribe = None
        self.motion_groups = {}
        self.motion.expand = lambda selected: expand_targets(
            self.hass, selected, self.motion_groups
        )
        self.dimmer = Dimmer(self.read_brightness, self.send_brightness, self.create_task)
        storage = (
            Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.levels")
            if hasattr(entry, "entry_id")
            else None
        )
        self.percentage = PercentageRamp(hass, self.create_task, storage=storage)
        self.dial_routing = DialRouting(clock=lambda: time.monotonic())

        self.control_devices = {}
        self.hold_directions = HoldDirections()
        self.native_commands = {}
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
        self.button_quiet_releases: dict[tuple[str, int], float] = {}
        self.button_ramp_timestamps: dict[tuple[str, int], float] = {}
        self.button_ramp_states: dict[tuple[str, int], dict[str, Any]] = {}
        self.gestures = Gestures(
            self.actions, self.emit_button, self.button_ready, self.button_hold_event
        )

    def create_task(self, coro) -> asyncio.Task:
        return self.entry.async_create_background_task(
            self.hass, coro, "Hue Reconfigo worker", eager_start=False
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
        await self.percentage.load()
        await self.motion.load()
        self.resources = await self.client.rotary_resources()
        self.tracker.baseline(self.resources)
        devices = await self.client.device_resources()
        if any(kind(item) == "motion" for item in devices):
            groups = []
            try:
                for resource_type in ("room", "zone"):
                    groups.extend(await motion_request(self.client, resource_type))
                registry = er.async_get(self.hass)
                entities = {
                    e.unique_id.rsplit(":", 1)[-1]: e.entity_id
                    for e in registry.entities.values()
                    if e.platform == HUE_DOMAIN
                    and e.config_entry_id == self.entry.data[CONF_HUE_ENTRY]
                    and e.entity_id.startswith("light.")
                }
                self.motion_groups = hue_group_members(devices, groups, entities)
            except BridgeError:
                _LOGGER.warning(
                    "Hue room membership unavailable; only exposed HA group members can be resolved"
                )
        rotary_owners = {item.get("owner", {}).get("rid") for item in self.resources}
        self.control_devices = {
            item["id"]: {
                "name": item.get("metadata", {}).get("name", item["id"]),
                "kind": kind(item),
                "services": item.get("services", []),
                "model": item.get("product_data", {}).get("model_id"),
            }
            for item in devices
            if item.get("id") not in rotary_owners and kind(item)
        }

    @callback
    def start(self) -> None:
        self.motion_entities = {}
        registry = er.async_get(self.hass)
        for resource, device in self.control_devices.items():
            if device["kind"] != "motion":
                continue
            services = {s["rtype"]: s["rid"] for s in device.get("services", [])}
            for entity in registry.entities.values():
                if (
                    entity.platform != HUE_DOMAIN
                    or entity.config_entry_id != self.entry.data[CONF_HUE_ENTRY]
                ):
                    continue
                role = motion_service_role(entity.entity_id, entity.unique_id, services)
                if role == "motion":
                    self.motion_entities[entity.entity_id] = resource
                elif role in ("lux", "motion_enabled", "lux_enabled"):
                    device[role + "_entity"] = entity.entity_id
        self.motion_unsubscribe = self.hass.bus.async_listen("state_changed", self.on_motion_state)
        self.unsubscribe = self.hass.bus.async_listen("hue_event", self.on_hue_event)
        self.task = self.create_task(self.poll())
        self.button_task = self.create_task(self.listen_buttons())
        self.button_poll_task = self.create_task(self.poll_buttons())

    async def reconfigure_motion(self, resource):
        """Discard only this motion's old cycle, then adopt current occupancy."""
        await self.motion.disable(resource)
        binding = controller_binding(self.entry, resource)
        if not binding.get("enabled"):
            return
        entity = next((e for e, r in self.motion_entities.items() if r == resource), None)
        state = self.hass.states.get(entity) if entity else None
        if not state or state.state != "on":
            return
        binding["motion_lux_entity"] = self.control_devices[resource].get("lux_entity", "")
        binding["motion_lux_enabled_entity"] = self.control_devices[resource].get(
            "lux_enabled_entity", ""
        )
        await self.motion.update(resource, binding, True)

    @callback
    def on_motion_state(self, event):
        entity = event.data.get("entity_id")
        if self.entry.options.get("motion_gate_enabled") and entity == self.entry.options.get(
            "motion_gate_entity"
        ):
            self.create_task(self.gate_changed())
        if entity and entity.startswith("light."):
            new_state = event.data.get("new_state")
            if new_state:
                self.motion.light_state(
                    entity,
                    new_state.state,
                    event.data.get("old_state").state if event.data.get("old_state") else None,
                )
        resource = self.motion_entities.get(entity)
        if not resource:
            return
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if (
            old is None
            or new is None
            or old.state not in ("on", "off")
            or new.state not in ("on", "off")
            or old.state == new.state
        ):
            return
        binding = controller_binding(self.entry, resource)
        binding["motion_lux_entity"] = self.control_devices[resource].get("lux_entity", "")
        binding["motion_lux_enabled_entity"] = self.control_devices[resource].get(
            "lux_enabled_entity", ""
        )
        self.motion.event(resource, binding, new.state == "on")

    def control_allowed(self, resource, binding=None):
        binding = binding or controller_binding(self.entry, resource)
        family = (
            binding.get("controller_kind")
            or self.control_devices.get(resource, {}).get("kind")
            or "dial"
        )
        return allows(self.hass, self.entry.options, "dial" if family == "tap_dial" else family)

    async def gate_changed(self):
        await self.motion.gate_changed()
        for resource, index in list(self.button_ramp_timestamps):
            if not self.control_allowed(resource):
                self.button_hold_event(resource, index, "release", time.monotonic())
        for key in list(self.percentage.ramps):
            if not self.control_allowed(key[0]):
                self.percentage.stop(key)

    def device(self, owner_id: str):
        return dr.async_get(self.hass).async_get_device_by_identifier(
            (HUE_DOMAIN, owner_id), self.entry.data[CONF_HUE_ENTRY]
        )

    def controllers(self) -> dict[str, str]:
        return {
            **{key: value["name"] for key, value in self.control_devices.items()},
            **{
                item["id"]: (
                    device.name_by_user or device.name or item["id"]
                    if (device := self.device(item["owner"]["rid"]))
                    else item["id"]
                )
                for item in self.resources
                if isinstance(item.get("id"), str) and item.get("owner", {}).get("rid")
            },
        }

    @callback
    def on_hue_event(self, event: Event) -> None:
        data = event.data
        if data.get("unique_id") in {item["id"] for item in self.resources}:
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
        actions = button_actions(binding, index) if binding.get("enabled") else {}
        if "long" in actions:
            actions["long_mode"] = button_long_mode(binding, index)[0]
        return actions

    def button_hold_event(self, resource_id: str, index: int, event: str, updated: float) -> None:
        """Run or stop the light ramp only for a configured long-dimming button."""
        binding = controller_binding(self.entry, resource_id)
        if event != "release" and not self.control_allowed(resource_id, binding):
            return
        mode, _ = button_long_mode(binding, index)
        if not binding.get("enabled") or mode != "dimming":
            return
        lights = tuple(sorted(set(targets(button_actions(binding, index).get("long")))))
        if not lights:
            return
        key = resource_id, index
        if all(entity.startswith(("fan.", "number.")) for entity in lights):
            if event == "start":
                self.percentage.cancel_entities(lights)
                self.button_ramp_timestamps[key] = updated
                self.percentage.start(key, lights, 0, RAMP_INITIAL_TRANSITION)
                ramp = self.percentage.ramps.get(key)
                if ramp:
                    direction = self.hold_directions.choose(
                        key,
                        sum(ramp.levels.values()) / len(ramp.levels),
                        binding.get(f"button_{index}", {}).get("long_direction"),
                    )
                    ramp.direction = 1 if direction == "up" else -1
                    self.percentage.advance(key, RAMP_STEP, RAMP_INITIAL_TRANSITION)
            elif event == "release":
                self.button_ramp_timestamps.pop(key, None)
                self.percentage.stop(key)
            elif event == "repeat" and key in self.button_ramp_timestamps:
                interval = updated - self.button_ramp_timestamps[key]
                self.button_ramp_timestamps[key] = updated
                if interval >= RAMP_DUPLICATE_REPEAT_WINDOW:
                    self.percentage.advance(
                        key, RAMP_STEP, max(RAMP_MIN_TRANSITION, min(RAMP_MAX_TRANSITION, interval))
                    )
            return
        if any(not entity.startswith("light.") for entity in lights):
            return
        if event == "start":
            self.motion.manual_action(lights)
            resources = self.hue_dimming_resources(lights)
            self.button_ramp_timestamps[key] = updated
            if resources:
                state = {
                    "resources": resources,
                    "lights": lights,
                    "direction": "up",
                    "fixed_direction": binding.get(f"button_{index}", {}).get("long_direction"),
                    "finished": False,
                    "pending": True,
                }
                self.button_ramp_states[key] = state
                task = self.create_task(self._start_button_ramp(key, state))
                self.action_tasks.add(task)
                task.add_done_callback(self.action_tasks.discard)
            else:
                # Keep supporting non-Hue light entities with the stepped fallback.
                direction = self.hold_directions.choose(
                    key,
                    self.read_brightness(lights) or 0,
                    binding.get(f"button_{index}", {}).get("long_direction"),
                )
                self.button_ramp_states[key] = {"resources": None, "direction": direction}
                self.dimmer.button_step(lights, direction, RAMP_INITIAL_TRANSITION, step=RAMP_STEP)
            return
        if event == "release":
            state = self.button_ramp_states.pop(key, None)
            self.button_ramp_timestamps.pop(key, None)
            if state and state.get("resources"):
                task = self.create_task(self._cancel_and_stop_native(state["resources"]))
            else:
                task = self.create_task(self.dimmer.stop_button_ramp(lights))
            self.action_tasks.add(task)
            task.add_done_callback(self.action_tasks.discard)
            return
        previous = self.button_ramp_timestamps.get(key)
        if event != "repeat" or previous is None:
            return
        self.button_ramp_timestamps[key] = updated
        interval = updated - previous
        # Hue reports an immediate repeat after long_press; it confirms the hold.
        if interval < RAMP_DUPLICATE_REPEAT_WINDOW:
            return
        state = self.button_ramp_states.get(key)
        if state is None:
            return
        resources = state.get("resources")
        if resources:
            if state.get("pending") or state.get("finished"):
                return
            if (state["direction"] == "up" and state["brightness"] >= 100) or (
                state["direction"] == "down" and state["brightness"] <= 0
            ):
                state["finished"] = True
                return
            delta = min(RAMP_STEP, 100 - state["brightness"])
            if state["direction"] == "down":
                delta = -min(RAMP_STEP, state["brightness"])
            duration_ms = round(max(RAMP_MIN_TRANSITION, min(RAMP_MAX_TRANSITION, interval)) * 1000)
            if state["direction"] == "down" and state["brightness"] <= RAMP_STEP:
                self._schedule_ramp_transition(resources, 0.0, duration_ms)
                state["brightness"] = 0.0
                state["finished"] = True
            else:
                self._schedule_brightness_delta(resources, delta, duration_ms)
                state["brightness"] = max(0.0, min(100.0, state["brightness"] + delta))
            return

        target = self.dimmer.targets.get(lights)
        if target and target.brightness is not None:
            if (state["direction"] == "up" and target.brightness >= 100) or (
                state["direction"] == "down" and target.brightness <= 0
            ):
                return
        transition = max(RAMP_MIN_TRANSITION, min(RAMP_MAX_TRANSITION, interval * 1.15))
        self.dimmer.button_step(lights, state["direction"], transition, step=RAMP_STEP)

    def hue_dimming_resources(self, lights: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
        """Map selected Hue light entities to their Hue API v2 light resources."""
        registry = er.async_get(self.hass)
        hue_entry_id = self.entry.data[CONF_HUE_ENTRY]
        resources = set()
        for entity_id in lights:
            entity = registry.async_get(entity_id)
            if (
                entity is None
                or entity.platform != HUE_DOMAIN
                or entity.config_entry_id != hue_entry_id
            ):
                return ()
            state = self.hass.states.get(entity_id)
            resource_type = (
                "grouped_light" if state and state.attributes.get("is_hue_group") else "light"
            )
            resource_id = entity.unique_id.rsplit(":", 1)[-1]
            resources.add((resource_type, resource_id))
        return tuple(sorted(resources))

    def _schedule_ramp_transition(
        self, resources: tuple[tuple[str, str], ...], brightness: float, duration_ms: int
    ) -> None:
        task = self.create_task(self._send_hue_transition(resources, brightness, duration_ms))
        pending = self.native_commands.setdefault(resources, set())
        pending.add(task)
        task.add_done_callback(pending.discard)
        self.action_tasks.add(task)
        task.add_done_callback(self.action_tasks.discard)

    async def _start_button_ramp(self, key: tuple[str, int], state: dict[str, Any]) -> None:
        """Read the actual Hue level, then begin with one small upward step."""
        await self.adaptive.mark(state["lights"])
        resources = state["resources"]
        try:
            levels = await asyncio.gather(
                *(
                    self.client.read_brightness(resource_type, resource_id)
                    for resource_type, resource_id in resources
                )
            )
        except Exception as err:
            _LOGGER.warning("Unable to read current Hue brightness: %s", err)
            levels = [max(0.0, min(100.0, self.read_brightness(state["lights"]) or 0.0))]
        if self.button_ramp_states.get(key) is not state:
            return
        current = sum(levels) / len(levels) if levels else 0.0
        state["brightness"] = current
        state["pending"] = False
        state["direction"] = self.hold_directions.choose(key, current, state.get("fixed_direction"))
        delta = (
            min(RAMP_STEP, 100 - current)
            if state["direction"] == "up"
            else -min(RAMP_STEP, current)
        )
        state["brightness"] = max(0.0, min(100.0, current + delta))
        duration_ms = round(RAMP_INITIAL_TRANSITION * 1000)
        if delta == 0:
            state["finished"] = True
            return
        if state["brightness"] == 0:
            self._schedule_ramp_transition(resources, 0.0, duration_ms)
            state["finished"] = True
        else:
            self._schedule_brightness_delta(resources, delta, duration_ms)
        _LOGGER.debug(
            "HFD_TRACE ramp_start key=%s bridge_brightness=%.1f delta=%.1f duration_ms=%d",
            key,
            current,
            delta,
            duration_ms,
        )

    def _schedule_brightness_delta(
        self,
        resources: tuple[tuple[str, str], ...],
        delta: float,
        duration_ms: int,
    ) -> None:
        task = self.create_task(self._send_brightness_delta(resources, delta, duration_ms))
        pending = self.native_commands.setdefault(resources, set())
        pending.add(task)
        task.add_done_callback(pending.discard)
        self.action_tasks.add(task)
        task.add_done_callback(self.action_tasks.discard)

    async def _send_brightness_delta(
        self,
        resources: tuple[tuple[str, str], ...],
        delta: float,
        duration_ms: int,
    ) -> None:
        results = await asyncio.gather(
            *(
                self.client.brightness_delta(resource_type, resource_id, delta, duration_ms)
                for resource_type, resource_id in resources
            ),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("Unable to update native Hue dimming", exc_info=result)

    async def _send_hue_transition(
        self, resources: tuple[tuple[str, str], ...], brightness: float, duration_ms: int
    ) -> None:
        results = await asyncio.gather(
            *(
                self.client.brightness_transition(
                    resource_type, resource_id, brightness, duration_ms
                )
                for resource_type, resource_id in resources
            ),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("Unable to start native Hue dimming", exc_info=result)

    async def stop_motion_ramps(self, levels):
        """Stop collateral Hue ramps natively; freeze other lights at estimated levels."""
        fallback = {}
        for entity, brightness in levels.items():
            resources = self.hue_dimming_resources((entity,))
            if resources:
                try:
                    for resource_type, resource_id in resources:
                        await self.client.stop_dimming(resource_type, resource_id)
                except BridgeError:
                    fallback[entity] = brightness
            else:
                fallback[entity] = brightness
        await self.motion.freeze_ramps(fallback)

    async def _cancel_and_stop_native(self, resources):
        pending = tuple(self.native_commands.pop(resources, ()))
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await self._stop_hue_transition(resources)

    async def _stop_hue_transition(self, resources: tuple[tuple[str, str], ...]) -> None:
        results = await asyncio.gather(
            *(
                self.client.stop_dimming(resource_type, resource_id)
                for resource_type, resource_id in resources
            ),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("Unable to stop native Hue dimming", exc_info=result)

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
        owners.update({key: key for key in self.control_devices})
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
            if self.button_quiet_releases.get(key) == updated and event == "short_release":
                first_seen = min(first_seen, checked - CLICK_WINDOW - QUIET_EPSILON)
            self.button_snapshots[key] = (updated, event, first_seen, checked)
            if not baseline and (previous is None or updated > previous[0]):
                self.wake_buttons()
                if key in self.button_gaps:
                    self.button_gaps[key] = max(self.button_gaps[key], updated)
                elif updated <= self.gestures.latest.get(key, float("-inf")):
                    # SSE may have delivered this exact transition just before
                    # the REST snapshot. It is already consumed, not evidence
                    # that polling skipped an intermediate button state.
                    continue
                else:
                    if event == "short_release" and key not in self.gestures.pending:
                        latest = self.gestures.latest.get(key, float("-inf"))
                        synthetic_press = max(latest + 0.000001, updated - 0.000001)
                        if synthetic_press < updated:
                            self.gestures.feed(*key, "initial_press", synthetic_press)
                    accepted_events = (
                        "initial_press",
                        "short_release",
                        "long_press",
                        "repeat",
                        "long_release",
                    )
                    accepted = event in accepted_events and self.gestures.feed(*key, event, updated)
                    if not accepted:
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
            created = None
            try:
                created_at = datetime.fromisoformat(envelope["creationtime"])
                if created_at.tzinfo is not None:
                    created = created_at.timestamp()
            except KeyError, TypeError, ValueError:
                pass
            for item in items:
                if not isinstance(item, dict) or item.get("type") != "button":
                    continue
                mapped = self.button_map.get(item.get("id"))
                report = self.button_report(item)
                if mapped and report:
                    updated, event = report
                    reports.append((updated, mapped, event, created))
        # Process the entire frame before any expiry callback can run.
        for updated, (resource_id, index), event, created in sorted(reports):
            key = resource_id, index
            if self.actions(resource_id, index):
                self.wake_buttons()
            self.gestures.feed(resource_id, index, event, updated)
            if event == "initial_press":
                self.button_quiet_releases.pop(key, None)
            elif (
                event == "short_release"
                and created is not None
                and created - updated >= CLICK_WINDOW
            ):
                self.button_quiet_releases[key] = updated
            gap = self.button_gaps.get(key)
            if gap is not None and self.gestures.latest.get(key, float("-inf")) >= gap:
                self.button_gaps.pop(key, None)
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
                    self.rotate_dial(report.resource_id, binding, report.signed_steps)
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

    def rotate_dial(self, controller: str, binding: dict, steps: int) -> None:
        if not binding.get("enabled") or not steps or not self.control_allowed(controller, binding):
            return
        borrowed = self.dial_routing.motion(controller)
        selected = tuple(borrowed or binding.get("lights", ()))
        if not percentage_targets(selected):
            return
        if all(entity.startswith("light.") for entity in selected):
            self.motion.manual_action(selected)
            self.dimmer.rotate({**binding, "lights": list(selected)}, steps)
        else:
            key = controller, 0
            ramp = self.percentage.ramps.get(key)
            if ramp and set(ramp.levels) != set(selected):
                self.percentage.stop(key)
            adaptive_options = (
                {"adaptive": True}
                if (
                    binding.get("dial_profile") in ("gentle", "balanced", "swift")
                    or binding.get("adaptive_transition", False)
                )
                else {}
            )
            self.percentage.rotate(
                key,
                selected,
                steps
                / 15
                * binding.get(
                    "nonlight_sensitivity",
                    1.5
                    if binding.get("dial_profile") == "custom"
                    else binding.get("sensitivity", 1.5),
                ),
                binding.get(
                    "nonlight_transition",
                    {"gentle": 1.0, "balanced": 0.75, "swift": 0.5}.get(
                        binding.get("dial_profile"),
                        0.75
                        if (binding.get("sensitivity", 1.5), binding.get("transition", 1.0))
                        == (1.5, 1.0)
                        else binding.get("transition", 1.0),
                    ),
                ),
                **adaptive_options,
            )

    async def send_brightness(
        self, lights: tuple[str, ...], brightness: float, transition: float
    ) -> None:
        if brightness <= 0:
            self.motion.manual_action(lights, off=True)
        await self.adaptive.mark(lights)
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
            if not self.control_allowed(resource_id, binding):
                return
            operation, percentage = button_operation(binding, index, action)
            if operation in ("step_up", "step_down"):
                selected = targets(button_actions(binding, index).get(action))
                self.motion.manual_action(selected)
                sign = 1 if operation == "step_up" else -1
                if selected and all(x.startswith("light.") for x in selected):
                    self.dimmer.button_step(
                        tuple(selected), "up" if sign > 0 else "down", 0.3, step=10
                    )
                elif selected:
                    for other_key, other_ramp in tuple(self.percentage.ramps.items()):
                        if other_key != (resource_id, index) and set(selected).intersection(
                            other_ramp.levels
                        ):
                            self.percentage.stop(other_key)
                    self.percentage.rotate((resource_id, index), selected, sign * 10, 0.3)
                return
            if (
                operation == "dial"
                and index > 1
                and binding.get("controller_kind", "tap_dial") == "tap_dial"
            ):
                selected = targets(button_actions(binding, index).get(action))
                if percentage_targets(selected):
                    self.dial_routing.borrow(resource_id, selected)
                    self.active_until = max(self.active_until, time.monotonic() + 5)
                    self.wake.set()
                return
            selected = targets(button_actions(binding, index).get(action))
            if not selected:
                return
            domain = selected[0].split(".", 1)[0]
            service = "toggle" if domain in ("light", "fan") else "turn_on"
            if domain not in ("light", "script", "fan", "number"):
                return
            if any(item.split(".", 1)[0] != domain for item in selected):
                return
            if domain not in ("light", "fan", "number") and len(selected) != 1:
                return
            startup = binding.get(f"button_{index}", {})
            startup = startup.get(f"{action}_startup") if isinstance(startup, dict) else None
            saved_levels = dict(self.motion.remembered) if domain == "light" and startup else {}
            if domain == "light":
                if operation in ("configured", "previous"):
                    for entity in selected:
                        state = self.hass.states.get(entity)
                        self.motion.manual_action([entity], off=bool(state and state.state == "on"))
                else:
                    is_off = operation == "off" or (
                        operation != "on"
                        and any(
                            (state := self.hass.states.get(entity)) is not None
                            and state.state == "on"
                            for entity in selected
                        )
                    )
                    self.motion.manual_action(selected, off=is_off)
            # Cancel the pending ramp before a button switches a light or scene.
            await self.dimmer.cancel_targets(tuple(set(binding.get("lights", [])).union(selected)))
            self.percentage.cancel_entities(selected)
            for key, ramp in tuple(self.button_ramp_states.items()):
                if set(selected).intersection(ramp.get("lights", ())):
                    self.button_ramp_states.pop(key, None)
                    self.button_ramp_timestamps.pop(key, None)
                    if ramp.get("resources"):
                        await self._cancel_and_stop_native(ramp["resources"])
            operation, percentage = button_operation(binding, index, action)
            if domain == "light" and (startup is not None or operation in ("on", "off")):
                await self.light_button_action(selected, startup or {}, saved_levels, operation)
                return
            if domain == "light" and operation in ("configured", "previous"):
                await self.adaptive.mark(selected)
            if domain == "number" or (domain in ("light", "fan") and operation != "toggle"):
                for entity in selected:
                    actual = None
                    if domain == "light" and operation == "previous":
                        resources = self.hue_dimming_resources((entity,))
                        if resources:
                            try:
                                actual = await self.client.read_brightness(*resources[0])
                            except BridgeError:
                                pass
                    await self.percentage.action(entity, operation, percentage, actual)
                return
            if domain == "script" and operation == "off":
                service = "turn_off"
            if domain == "light":
                # Resolve the whole selection before Adaptive Lighting can intercept
                # a toggle. Unavailable/missing members cannot count as lit.
                service = (
                    "turn_off"
                    if any(
                        (state := self.hass.states.get(entity)) is not None and state.state == "on"
                        for entity in selected
                    )
                    else "turn_on"
                )
            await self.hass.services.async_call(
                domain,
                service,
                {"entity_id": selected if domain in ("light", "fan") else selected[0]},
                blocking=True,
            )

    async def light_button_action(self, selected, startup, saved_levels, operation="toggle"):
        """Share Motion's startup appearance and pre-fade brightness recovery."""
        lights = sorted(self.motion.expand(selected))
        any_on = any(
            (state := self.hass.states.get(entity)) is not None and state.state == "on"
            for entity in lights
        )
        if operation == "off" or (operation != "on" and any_on):
            for entity in lights:
                state = self.hass.states.get(entity)
                if state is None or state.state != "on":
                    continue
                level = state.attributes.get("brightness")
                resources = self.hue_dimming_resources((entity,))
                if resources:
                    try:
                        actual = await self.client.read_brightness(*resources[0])
                        if actual is not None:
                            level = round(actual * 255 / 100)
                    except BridgeError:
                        pass
                if isinstance(level, (int, float)) and 0 < level <= 255:
                    self.motion.remembered[entity] = {"brightness": level, "owner": "controller"}
            await self.motion.persist()
            await self.hass.services.async_call(
                "light", "turn_off", {"entity_id": selected}, blocking=True
            )
            return
        for entity in lights:
            if entity in saved_levels:
                self.motion.remembered[entity] = saved_levels[entity]
            elif entity not in self.motion.remembered and entity in self.percentage.previous:
                # Migrate a previously saved button percentage without losing its value.
                self.motion.remembered[entity] = {
                    "brightness": max(1, round(self.percentage.previous[entity] * 255 / 100)),
                    "owner": "controller",
                }
        await self.motion.turn_on(lights, {"motion_start": startup})

    async def close(self) -> None:
        self.closed = True
        if self.motion_unsubscribe:
            self.motion_unsubscribe()
        await self.motion.close()
        self.dial_routing.close()
        if self.unsubscribe:
            self.unsubscribe()
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        self.gestures.cancel()
        resources = {
            state["resources"]
            for state in self.button_ramp_states.values()
            if state.get("resources")
        }
        self.button_ramp_states.clear()
        for selected in resources:
            await self._cancel_and_stop_native(selected)
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
        await self.percentage.close()
