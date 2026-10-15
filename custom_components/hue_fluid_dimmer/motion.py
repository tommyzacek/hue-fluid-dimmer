"""Event-driven motion lighting with a cancellable pre-off warning."""

import asyncio
import logging
import math
import time

from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .adaptive import members
from .gate import allows
from .motion_schedule import effective_binding, validate_periods

_LOGGER = logging.getLogger(__name__)


class MotionLighting:
    def __init__(self, hass, create_task, adaptive, storage=None):
        self.hass, self.create_task, self.adaptive = hass, create_task, adaptive
        self.sessions = {}
        self.tasks = set()
        self.closed = False
        self.storage = storage
        self.remembered = {}
        self.persist_lock = asyncio.Lock()
        self.now = dt_util.now
        self.overrides = {}
        self.locks = {}
        self.stop_ramps = self.freeze_ramps
        self.expand = lambda selected: (
            set().union(*(members(self.hass, e) for e in selected)) if selected else set()
        )
        self.clock = time.monotonic
        self.gate_options = lambda: {}

    def allowed(self):
        """Require an explicit matching state; unavailable sources never grant control."""
        return allows(self.hass, self.gate_options(), "motion")

    async def gate_changed(self):
        """Let existing cycles expire when motion may no longer extend them."""
        if self.allowed():
            return
        for resource in list(self.sessions):
            async with self.locks.setdefault(resource, asyncio.Lock()):
                session = self.sessions.get(resource)
                if session and session["occupied"]:
                    await self._update(resource, session["binding"], False)

    async def load(self):
        if self.storage:
            saved = await self.storage.async_load()
            if isinstance(saved, dict) and saved.get("format") == 2:
                self.remembered = {
                    e: value
                    for e, value in saved.get("levels", {}).items()
                    if isinstance(e, str)
                    and isinstance(value, dict)
                    and isinstance(value.get("brightness"), (int, float))
                    and 1 <= value["brightness"] <= 255
                }

    async def persist(self):
        if self.storage:
            async with self.persist_lock:
                await self.storage.async_save({"format": 2, "levels": dict(self.remembered)})

    def forget(self, entities):
        changed = any(e in self.remembered for e in entities)
        for entity in entities:
            self.remembered.pop(entity, None)
        if changed and self.storage:
            self.schedule(self.persist())

    async def turn_on(self, selected, binding):
        options = {**START_DEFAULTS, **binding.get("motion_start", {})}
        brightness_mode = options["brightness"]
        color_mode = options["color"]
        # Unchanged defaults follow the original service call, including AL behavior.
        if (
            brightness_mode == "unchanged"
            and color_mode == "unchanged"
            and not any(e in self.remembered for e in selected)
        ):
            await self.call("turn_on", selected, transition=0.5)
            return
        planned, consumed = {}, {}
        for entity in selected:
            state = self.hass.states.get(entity)
            attributes = state.attributes if state else {}
            data = {"transition": 0.5}
            if brightness_mode == "configured":
                data["brightness_pct"] = options["percentage"]
            remembered = self.remembered.pop(entity, None)
            if brightness_mode == "unchanged" and remembered and state and state.state == "off":
                data["brightness"] = remembered["brightness"]
                consumed[entity] = remembered
            supported = attributes.get("supported_color_modes", [])
            if color_mode == "temperature" and "color_temp" in supported:
                low = attributes.get("min_color_temp_kelvin", 2000)
                high = attributes.get("max_color_temp_kelvin", 6500)
                data["color_temp_kelvin"] = max(low, min(high, options["temperature"]))
            elif color_mode == "rgb" and set(supported).intersection(
                ("hs", "xy", "rgb", "rgbw", "rgbww")
            ):
                data["rgb_color"] = options["rgb"]
            explicit_brightness = "brightness_pct" in data
            explicit_color = "color_temp_kelvin" in data or "rgb_color" in data
            if explicit_brightness or explicit_color:
                component = (
                    "both"
                    if explicit_brightness and explicit_color
                    else ("brightness" if explicit_brightness else "color")
                )
                await self.adaptive.mark([entity], component=component)
            key = repr(sorted(data.items()))
            planned.setdefault(key, (data, []))[1].append(entity)
        pending = set(consumed)
        try:
            for data, entities in planned.values():
                await self.call("turn_on", entities, **data)
                pending.difference_update(entities)
        except HomeAssistantError, asyncio.CancelledError:
            self.remembered.update({e: consumed[e] for e in pending})
            await self.persist()
            raise
        await self.persist()

    def schedule(self, coro):
        task = self.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def call(self, service, lights, **kwargs):
        await self.hass.services.async_call(
            "light",
            service,
            {"entity_id": list(lights), **kwargs},
            blocking=True,
            context=Context(),
        )

    def event(self, resource, binding, active):
        if not binding.get("enabled") or self.closed:
            return
        self.schedule(self.update(resource, binding, active))

    def capture(self, entity):
        state = self.hass.states.get(entity)
        if state is None or state.state not in ("on", "off"):
            return None
        data = {}
        attributes = state.attributes
        if isinstance(attributes.get("brightness"), (int, float)):
            data["brightness"] = attributes["brightness"]
        mode = attributes.get("color_mode")
        if mode == "color_temp" and attributes.get("color_temp_kelvin") is not None:
            data["color_temp_kelvin"] = attributes["color_temp_kelvin"]
        elif mode in ("hs", "xy", "rgb", "rgbw", "rgbww"):
            key = mode + "_color"
            if attributes.get(key) is not None:
                data[key] = attributes[key]
        return data

    def release_overrides(self, resource, active):
        overrides = self.overrides.get(resource, {})
        for entity, rule in tuple(overrides.items()):
            state = self.hass.states.get(entity)
            if rule["return"] == "off" and state and state.state == "off":
                overrides.pop(entity, None)
            elif rule["return"] == "idle":
                deadline = rule.get("deadline")
                if active and deadline is not None and self.clock() >= deadline:
                    overrides.pop(entity, None)
                elif active:
                    rule["deadline"] = None
                else:
                    rule["deadline"] = self.clock() + rule["seconds"]
        return set(overrides)

    def light_state(self, entity, state, previous=None):
        if state == "on" and previous == "off":
            self.forget([entity])
        # A state change only ends a known manual handover; it never creates one.
        if state != "off":
            return
        for overrides in self.overrides.values():
            rule = overrides.get(entity)
            if rule and rule["return"] == "off":
                overrides.pop(entity, None)

    async def update(self, resource, binding, active):
        async with self.locks.setdefault(resource, asyncio.Lock()):
            await self._update(resource, binding, active)

    async def _update(self, resource, binding, active):
        if active and not self.allowed():
            return
        policy = {**POLICY_DEFAULTS, **binding.get("motion_behavior", {})}
        excluded = self.release_overrides(resource, active)
        session = self.sessions.get(resource)
        if active:
            if session:
                session["occupied"] = True
                if session.get("timer"):
                    session["timer"].cancel()
                if session.get("warning"):
                    session["warning"] = False
                    await self.restore(session)
                # Rejoin only released handovers or explicitly allowed manual-off targets.
                returning = (session["handed"] - excluded) | session["restart"]
                session["handed"].intersection_update(excluded)
                session["restart"].clear()
                returning -= session["blocked"]
                if returning:
                    await self.adopt(session, returning)
                return
            if binding.get("motion_periods") is not None:
                binding = effective_binding(binding, self.now())
                if binding is None:
                    return
            allow_on = True
            if binding.get("motion_use_lux", False):
                enabled_entity = binding.get("motion_lux_enabled_entity")
                enabled = self.hass.states.get(enabled_entity) if enabled_entity else None
                if enabled_entity and (enabled is None or enabled.state != "on"):
                    allow_on = False
                lux = self.hass.states.get(binding.get("motion_lux_entity", ""))
                try:
                    value = float(lux.state)
                    if not math.isfinite(value) or value >= binding.get("motion_lux", 50):
                        allow_on = False
                except AttributeError, ValueError, TypeError:
                    allow_on = False
            targets = self.expand(binding.get("motion_targets", [])) - excluded
            targets = {
                e
                for e in targets
                if (state := self.hass.states.get(e))
                and (state.state == "on" or (allow_on and state.state == "off"))
            }
            if not targets:
                return
            session = {
                "lights": set(),
                "initial": {},
                "seen": set(),
                "allow_on": allow_on,
                "occupied": True,
                "warning": False,
                "timer": None,
                "snapshot": {},
                "leases": [],
                "binding": binding,
                "policy": policy,
                "blocked": set(),
                "restart": set(),
                "handed": set(excluded),
            }
            self.sessions[resource] = session
            try:
                await self.adopt(session, targets)
            except HomeAssistantError as err:
                self.sessions.pop(resource, None)
                _LOGGER.warning("Unable to activate motion lights: %s", err)
            return
        if session:
            if not self.allowed() and not session["occupied"]:
                return
            session["occupied"] = False
            if session.get("timer"):
                session["timer"].cancel()
            task = self.create_task(self.countdown(resource, session))
            session["timer"] = task
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

    async def adopt(self, session, targets):
        selected = []
        for entity in sorted(targets):
            state = self.hass.states.get(entity)
            if not state or state.state not in ("on", "off"):
                continue
            session["lights"].add(entity)
            if entity not in session["seen"]:
                session["seen"].add(entity)
                if state.state == "on":
                    session["initial"][entity] = self.capture(entity) or {}
            if session["allow_on"] and (
                state.state == "off" or session["policy"]["arrival"] == "apply"
            ):
                selected.append(entity)
        if selected:
            await self.turn_on(selected, session["binding"])

    def valid(self, resource, session):
        return (
            not self.closed and self.sessions.get(resource) is session and not session["occupied"]
        )

    def ending_targets(self, session):
        if session["policy"]["departure"] == "off":
            return set(session["lights"])
        return set(session["lights"]) - session["initial"].keys()

    async def countdown(self, resource, session):
        binding = session["binding"]
        total = max(60, binding.get("motion_timeout", 300))
        warning = (
            min(30, total)
            if binding.get("motion_soft_end", binding.get("motion_warning", 30) > 0)
            else 0
        )
        mode = binding.get("motion_end_mode", "half")
        try:
            await asyncio.sleep(total - warning)
            if not self.valid(resource, session):
                return
            snapshot = {}
            for entity in self.ending_targets(session):
                state = self.hass.states.get(entity)
                if (
                    state
                    and state.state == "on"
                    and isinstance(state.attributes.get("brightness"), (int, float))
                ):
                    snapshot[entity] = state.attributes["brightness"]
            session["snapshot"] = snapshot
            if warning and snapshot:
                session["leases"] = await self.adaptive.pause(snapshot)
                if not self.valid(resource, session):
                    return
                self.remembered.update(
                    {e: {"brightness": level, "owner": resource} for e, level in snapshot.items()}
                )
                await self.persist()
                session["warning"] = True
                session["ramp_started"] = self.clock()
                session["ramp_duration"] = 2 if mode == "half_quick" else warning
                for entity, brightness in tuple(snapshot.items()):
                    if not self.valid(resource, session):
                        return
                    if entity not in session["lights"] or entity not in session["snapshot"]:
                        continue
                    if mode == "fade":
                        await self.call("turn_off", [entity], transition=warning)
                    else:
                        await self.call(
                            "turn_on",
                            [entity],
                            brightness=max(1, round(brightness * 0.5)),
                            transition=session["ramp_duration"],
                        )
            await asyncio.sleep(warning)
            async with self.locks.setdefault(resource, asyncio.Lock()):
                if not self.valid(resource, session):
                    return
                selected = self.ending_targets(session)
                if selected:
                    await self.call("turn_off", sorted(selected), transition=2)
                if session["policy"]["departure"] == "restore":
                    for entity, data in tuple(session["initial"].items()):
                        if not self.valid(resource, session):
                            return
                        if entity in session["lights"]:
                            await self.call("turn_on", [entity], **data, transition=0.7)
                self.sessions.pop(resource, None)
                await self.adaptive.release(session["leases"])
        except asyncio.CancelledError:
            raise
        except HomeAssistantError as err:
            _LOGGER.warning("Motion lighting action failed: %s", err)
            self.sessions.pop(resource, None)

    async def restore(self, session):
        for entity, brightness in tuple(session["snapshot"].items()):
            state = self.hass.states.get(entity)
            if entity in session["lights"] and state and state.state in ("on", "off"):
                await self.call("turn_on", [entity], brightness=brightness, transition=0.5)
        self.forget(list(session["snapshot"]))
        await self.adaptive.release(session["leases"])
        session["leases"] = []
        session["snapshot"] = {}

    def manual_action(self, selected, off=False):
        if not self.sessions:
            return
        changed = self.expand([e for e in selected if e.startswith("light.")])
        self.forget(changed)
        for resource, session in tuple(self.sessions.items()):
            touched = changed & set(session["lights"])
            if not touched:
                continue
            policy = session["policy"]
            if policy["manual_scope"] == "all" and (off or policy["manual_change"] == "handover"):
                touched = set(session["lights"])
            # Only collateral lights need a separate stop. The controller's own
            # command supersedes the ramp for its directly changed targets.
            self.forget(touched)
            collateral = touched - changed
            running = collateral & session["snapshot"].keys()
            if (
                running
                and session.get("warning")
                and (off or policy["manual_change"] == "handover")
            ):
                elapsed = max(0, self.clock() - session["ramp_started"])
                fraction = min(1, elapsed / session["ramp_duration"])
                end_factor = 0 if session["binding"].get("motion_end_mode") == "fade" else 0.5
                levels = {
                    e: max(1, round(session["snapshot"][e] * (1 - fraction * (1 - end_factor))))
                    for e in running
                }
                self.schedule(self.stop_ramps(levels))
            # A controller's manual AL flag must not be cleared by our old lease.
            session["leases"] = [
                (switch, remaining, legacy)
                for switch, lights, legacy in session["leases"]
                if (remaining := [entity for entity in lights if entity not in touched])
            ]
            # Never restore a pre-manual-change snapshot over the user's new choice.
            for entity in touched if off or policy["manual_change"] == "handover" else changed:
                session["snapshot"].pop(entity, None)
            if off:
                session["lights"].difference_update(touched)
                if policy["manual_off"] == "resume":
                    session["restart"].update(touched)
                else:
                    session["blocked"].update(touched)
            elif policy["manual_change"] == "handover":
                session["lights"].difference_update(touched)
                session["handed"].update(touched)
                rules = self.overrides.setdefault(resource, {})
                for entity in touched:
                    rules[entity] = {
                        "return": policy["return"],
                        "seconds": policy["return_seconds"],
                        "deadline": None
                        if session["occupied"]
                        else self.clock() + policy["return_seconds"],
                    }

    async def freeze_ramps(self, levels):
        for entity, brightness in levels.items():
            await self.call("turn_on", [entity], brightness=brightness, transition=0)

    def cancel_targets(self, selected):
        # Compatibility for controllers: a change is not automatically a handover.
        self.manual_action(selected)

    async def disable(self, resource):
        async with self.locks.setdefault(resource, asyncio.Lock()):
            session = self.sessions.pop(resource, None)
            self.overrides.pop(resource, None)
            self.forget([e for e, data in self.remembered.items() if data.get("owner") == resource])
            if session:
                task = session.get("timer")
                if task:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                if session.get("warning") and session["snapshot"]:
                    elapsed = max(0, self.clock() - session["ramp_started"])
                    fraction = min(1, elapsed / session["ramp_duration"])
                    factor = 0 if session["binding"].get("motion_end_mode") == "fade" else 0.5
                    await self.stop_ramps(
                        {
                            e: max(1, round(level * (1 - fraction * (1 - factor))))
                            for e, level in session["snapshot"].items()
                            if e in session["lights"]
                        }
                    )
                await self.adaptive.release(session["leases"])

    async def close(self):
        self.closed = True
        for task in tuple(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        # Never restore old brightness or switch lights off during an unload.
        self.sessions.clear()
        self.overrides.clear()
        await self.persist()


START_DEFAULTS = {
    "brightness": "unchanged",
    "percentage": 50,
    "color": "unchanged",
    "temperature": 2700,
    "rgb": [255, 180, 100],
}

POLICY_DEFAULTS = {
    "arrival": "apply",
    "departure": "off",
    "manual_change": "continue",
    "manual_off": "hold",
    "manual_scope": "touched",
    "return": "off",
    "return_seconds": 300,
}

DEFAULTS = {
    "enabled": False,
    "motion_targets": [],
    "motion_start": START_DEFAULTS,
    "motion_periods": None,
    "motion_behavior": POLICY_DEFAULTS,
    "motion_timeout": 300,
    "motion_soft_end": True,
    "motion_end_mode": "half",
    "motion_use_lux": False,
    "motion_lux": 50,
    "motion_sensitivity": None,
}


def parse_motion(values):
    if "motion_lux_slider" in values:
        slider = values["motion_lux_slider"]
        values = {
            **values,
            "motion_use_lux": slider <= 650,
            "motion_lux": slider if slider <= 650 else DEFAULTS["motion_lux"],
        }
    values = {
        **values,
        "motion_soft_end": values.get("motion_soft_end", values.get("motion_warning", 30) > 0),
    }
    binding = {
        **DEFAULTS,
        **{key: value for key, value in values.items() if key in DEFAULTS},
        "controller_kind": "motion",
    }
    startup = binding.get("motion_start")
    if not isinstance(startup, dict):
        return binding, "motion_start_invalid"
    startup = {**START_DEFAULTS, **startup}
    binding["motion_start"] = startup
    if startup["brightness"] == "previous":
        startup["brightness"] = "unchanged"
    if startup["brightness"] not in ("unchanged", "configured") or startup["color"] not in (
        "unchanged",
        "temperature",
        "rgb",
    ):
        return binding, "motion_start_invalid"
    if not isinstance(startup["percentage"], (int, float)) or not 1 <= startup["percentage"] <= 100:
        return binding, "motion_start_invalid"
    if (
        not isinstance(startup["temperature"], (int, float))
        or not 1500 <= startup["temperature"] <= 10000
    ):
        return binding, "motion_start_invalid"
    if (
        not isinstance(startup["rgb"], list)
        or len(startup["rgb"]) != 3
        or any(not isinstance(v, int) or not 0 <= v <= 255 for v in startup["rgb"])
    ):
        return binding, "motion_start_invalid"
    startup["temperature"] = int(startup["temperature"] / 100 + 0.5) * 100
    policy = binding.get("motion_behavior")
    if not isinstance(policy, dict):
        return binding, "motion_behavior_invalid"
    policy = {**POLICY_DEFAULTS, **policy}
    binding["motion_behavior"] = policy
    for field, choices in {
        "arrival": ("apply", "keep"),
        "departure": ("off", "keep", "restore"),
        "manual_change": ("continue", "handover"),
        "manual_off": ("resume", "hold"),
        "manual_scope": ("touched", "all"),
        "return": ("off", "idle"),
    }.items():
        if policy[field] not in choices:
            return binding, "motion_behavior_invalid"
    if (
        not isinstance(policy["return_seconds"], (int, float))
        or not 10 <= policy["return_seconds"] <= 86400
    ):
        return binding, "motion_behavior_invalid"
    selected = binding["motion_targets"]
    if (
        not isinstance(selected, list)
        or (binding["enabled"] and not selected)
        or any(not isinstance(e, str) or not e.startswith("light.") for e in selected)
    ):
        return binding, "motion_targets_required"
    if binding["motion_end_mode"] not in ("half", "fade", "half_quick"):
        return binding, "motion_end_invalid"
    if binding.get("motion_periods") is not None:
        try:
            binding["motion_periods"] = validate_periods(binding["motion_periods"], parse_motion)
        except ValueError:
            return binding, "motion_periods_invalid"
    return binding, None
