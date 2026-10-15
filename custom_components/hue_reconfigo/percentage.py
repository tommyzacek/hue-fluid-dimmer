"""Smooth held-button control of HA fan and number percentages."""

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field

_LOGGER = logging.getLogger(__name__)


@dataclass
class Ramp:
    levels: dict[str, float]
    bounds: dict[str, tuple[float, float, float]]
    starts: dict[str, float] = field(default_factory=dict)
    goals: dict[str, float] = field(default_factory=dict)
    sent: dict[str, float] = field(default_factory=dict)
    started: float = 0
    duration: float = 0.8
    direction: int = 1
    pause: bool = False
    task: asyncio.Task | None = None


class PercentageRamp:
    def __init__(self, hass, create_task, tick=0.1, storage=None):
        self.hass, self.create_task, self.tick = hass, create_task, tick
        self.ramps: dict[tuple[str, int], Ramp] = {}
        self.storage = storage
        self.previous: dict[str, float] = {}

    async def load(self):
        if self.storage is not None:
            data = await self.storage.async_load() or {}
            self.previous = {
                entity: value
                for entity, value in data.get("previous", {}).items()
                if isinstance(value, (int, float)) and 0 < value <= 100
            }

    def cancel_entities(self, entities):
        for key, ramp in tuple(self.ramps.items()):
            if set(entities).intersection(ramp.levels):
                self.stop(key)

    async def action(self, entity, operation, percentage, actual_level=None):
        """Toggle power, restore the previous level, or toggle to a configured level."""
        state = self.hass.states.get(entity)
        if state is None or state.state in ("unavailable", "unknown"):
            return
        domain = entity.split(".", 1)[0]
        low, high, quantum = 0.0, 100.0, 1.0
        try:
            if domain == "number":
                low, high = float(state.attributes["min"]), float(state.attributes["max"])
                quantum = float(state.attributes.get("step", 1))
                if high <= low or quantum <= 0:
                    return
                current = (float(state.state) - low) * 100 / (high - low)
            elif state.state == "off":
                current = 0.0
            elif actual_level is not None:
                current = actual_level
            elif domain == "light":
                current = (state.attributes.get("brightness") or 255) / 255 * 100
            else:
                current = float(state.attributes.get("percentage") or 100)
            if not all(math.isfinite(x) for x in (low, high, quantum, current)):
                return
        except KeyError, TypeError, ValueError:
            return
        if current > 0 and operation != "on":
            self.previous[entity] = max(0, min(100, current))
            if self.storage is not None:
                await self.storage.async_save({"previous": dict(self.previous)})
            desired = 0.0
        elif operation == "off":
            desired = 0.0
        elif operation == "previous":
            desired = self.previous.get(entity)
            if desired is None:
                if domain in ("light", "fan"):
                    await self.hass.services.async_call(
                        domain, "turn_on", {"entity_id": entity}, blocking=True
                    )
                else:
                    _LOGGER.warning(
                        "No previous level recorded for %s; set a nonzero value first", entity
                    )
                return
        else:
            desired = percentage if operation in ("configured", "on") else 100.0
        data = {"entity_id": entity}
        if domain == "number":
            raw = low + desired * (high - low) / 100
            value = max(low, min(high, low + round((raw - low) / quantum) * quantum))
            if desired <= 0:
                value = low
            elif desired >= 100:
                value = high
            service, data["value"] = "set_value", value
        elif domain == "fan":
            service, data["percentage"] = "set_percentage", round(desired)
        else:
            service = "turn_on" if desired > 0 else "turn_off"
            if desired > 0:
                data["brightness_pct"] = max(1, round(desired))
        await self.hass.services.async_call(domain, service, data, blocking=True)

    def start(self, key, entities, step, duration):
        self.stop(key)
        levels, bounds = {}, {}
        for entity in entities:
            state = self.hass.states.get(entity)
            if state is None or state.state in ("unknown", "unavailable"):
                return
            try:
                if entity.startswith("number."):
                    low, high = float(state.attributes["min"]), float(state.attributes["max"])
                    quantum = float(state.attributes.get("step", 1))
                    value = float(state.state)
                else:
                    low, high = 0.0, 100.0
                    quantum = float(state.attributes.get("percentage_step", 1))
                    value = 0.0 if state.state == "off" else float(state.attributes["percentage"])
                if (
                    high <= low
                    or quantum <= 0
                    or not all(math.isfinite(x) for x in (low, high, quantum, value))
                ):
                    return
            except KeyError, TypeError, ValueError:
                return
            levels[entity] = max(0, min(100, (value - low) * 100 / (high - low)))
            bounds[entity] = low, high, quantum
        self.ramps[key] = Ramp(levels, bounds)
        self.advance(key, step, duration)

    def advance(self, key, step, duration):
        ramp = self.ramps.get(key)
        if ramp is None:
            return
        goals = ramp.goals or ramp.levels
        if (ramp.direction > 0 and all(value >= 100 for value in goals.values())) or (
            ramp.direction < 0 and all(value <= 0 for value in goals.values())
        ):
            return
        ramp.starts = dict(ramp.levels)
        ramp.goals = {
            entity: max(0, min(100, value + ramp.direction * step))
            for entity, value in goals.items()
        }
        ramp.started, ramp.duration = time.monotonic(), max(0.01, duration)
        if ramp.task is None or ramp.task.done():
            ramp.task = self.create_task(self._run(key, ramp))

    def rotate(self, key, entities, delta, duration, adaptive=False):
        ramp = self.ramps.get(key)
        if ramp is None or (
            time.monotonic() - ramp.started > 3 and (ramp.task is None or ramp.task.done())
        ):
            self.start(key, entities, 0, duration)
            ramp = self.ramps.get(key)
        if ramp is None:
            return
        goals = ramp.goals or ramp.levels
        if adaptive:
            elapsed = time.monotonic() - ramp.started
            duration = min(
                duration, max(0.15, min(0.5, elapsed if 0.15 <= elapsed <= 0.8 else 0.4))
            )
            direction = 1 if delta > 0 else -1
            if getattr(ramp, "dial_direction", direction) != direction:
                goals = ramp.levels
            ramp.dial_direction = direction
        ramp.starts = dict(ramp.levels)
        ramp.goals = {entity: max(0, min(100, value + delta)) for entity, value in goals.items()}
        ramp.started, ramp.duration = time.monotonic(), max(0.01, duration)
        if ramp.task is None or ramp.task.done():
            ramp.task = self.create_task(self._run(key, ramp))

    async def _run(self, key, ramp):
        try:
            while self.ramps.get(key) is ramp:
                progress = min(1.0, (time.monotonic() - ramp.started) / ramp.duration)
                for entity, goal in ramp.goals.items():
                    level = ramp.starts[entity] + (goal - ramp.starts[entity]) * progress
                    ramp.levels[entity] = level
                    low, high, quantum = ramp.bounds[entity]
                    raw = low + level * (high - low) / 100
                    value = max(low, min(high, low + round((raw - low) / quantum) * quantum))
                    if ramp.sent.get(entity) == value:
                        continue
                    domain = entity.split(".", 1)[0]
                    service = "set_percentage" if domain == "fan" else "set_value"
                    field_name = "percentage" if domain == "fan" else "value"
                    await self.hass.services.async_call(
                        domain, service, {"entity_id": entity, field_name: value}, blocking=True
                    )
                    ramp.sent[entity] = value
                if progress >= 1:
                    return
                await asyncio.sleep(self.tick)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.warning("Percentage ramp command failed", exc_info=True)
            self.ramps.pop(key, None)

    def stop(self, key):
        ramp = self.ramps.pop(key, None)
        if ramp and ramp.task:
            ramp.task.cancel()

    async def close(self):
        tasks = [ramp.task for ramp in self.ramps.values() if ramp.task]
        for key in tuple(self.ramps):
            self.stop(key)
        await asyncio.gather(*tasks, return_exceptions=True)
