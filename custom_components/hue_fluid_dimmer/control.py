"""In-memory dimming targets and serial, coalesced light commands."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)


@dataclass
class Target:
    brightness: float | None = None
    last_motion: float = 0
    revision: int = 0
    direction: int = 0
    transition: float = 1
    command_start_brightness: float | None = None
    command_target_brightness: float | None = None
    command_started: float = 0
    command_transition: float = 0
    task: asyncio.Task | None = None


class Dimmer:
    """Share one target for identical light selections; no helper entities."""

    def __init__(
        self,
        read_brightness: Callable[[tuple[str, ...]], float | None],
        send: Callable[[tuple[str, ...], float, float], Awaitable[None]],
        create_task: Callable[[Awaitable[None]], asyncio.Task] = asyncio.create_task,
        clock: Callable[[], float] = time.monotonic,
        command_interval: float = 0.25,
    ) -> None:
        self.read_brightness = read_brightness
        self.send = send
        self.create_task = create_task
        self.clock = clock
        self.command_interval = command_interval
        self.targets: dict[tuple[str, ...], Target] = {}

    def rotate(self, binding: dict, steps: int) -> None:
        lights = tuple(sorted(set(binding.get("lights", []))))
        if not binding.get("enabled") or not lights:
            return
        target = self.targets.setdefault(lights, Target())
        now = self.clock()
        if target.brightness is None or (now - target.last_motion > 3 and target.task is None):
            target.brightness = self.read_brightness(lights)
        if target.brightness is None:
            return  # All selected lights are unavailable: do not guess a target.
        adaptive = binding.get("dial_profile") == "custom" and binding.get(
            "adaptive_transition", False
        )
        if adaptive and target.command_target_brightness is None:
            target.command_start_brightness = target.brightness
            target.command_target_brightness = target.brightness
            target.command_started = now
            target.command_transition = 0
        direction = 1 if steps > 0 else -1
        elapsed = now - target.last_motion
        if adaptive and target.direction and target.direction != direction:
            target.brightness = self._current_command_brightness(target, now)
        target.direction = direction
        target.brightness = max(
            0, min(100, target.brightness + steps / 15 * binding.get("sensitivity", 1.5))
        )
        target.last_motion = now
        target.transition = binding.get("transition", 1.0)
        if adaptive:
            # Report cadence, not the requested endpoint, determines the next segment.
            cadence = elapsed if 0.15 <= elapsed <= 0.8 else 0.4
            target.transition = min(target.transition, max(0.15, min(0.5, cadence)))
        target.revision += 1
        if target.task is None:
            target.task = self.create_task(self._run(lights, target))

    def button_step(
        self,
        lights: tuple[str, ...],
        direction: str,
        transition: float,
        step: float = 5.0,
    ) -> None:
        """Advance a held-button ramp from its last commanded brightness."""
        lights = tuple(sorted(set(lights)))
        if not lights:
            return
        target = self.targets.setdefault(lights, Target())
        now = self.clock()
        if target.brightness is None or (now - target.last_motion > 3 and target.task is None):
            target.brightness = self.read_brightness(lights)
        if target.brightness is None:
            return
        if target.command_target_brightness is None:
            target.command_start_brightness = target.brightness
            target.command_target_brightness = target.brightness
            target.command_started = now
            target.command_transition = 0
        delta = step if direction == "up" else -step
        target.brightness = max(0, min(100, target.brightness + delta))
        target.last_motion = now
        target.transition = max(0, transition)
        target.revision += 1
        if target.task is None:
            target.task = self.create_task(self._run(lights, target))

    async def stop_button_ramp(self, lights: tuple[str, ...]) -> None:
        """Cancel pending ramp work and hold its current interpolated brightness."""
        lights = tuple(sorted(set(lights)))
        target = self.targets.get(lights)
        if target is None:
            return
        task = target.task
        if task and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        brightness = self._current_command_brightness(target, self.clock())
        if brightness is not None:
            target.brightness = brightness
            target.command_start_brightness = brightness
            target.command_target_brightness = brightness
            target.command_started = self.clock()
            target.command_transition = 0
        target.revision += 1
        if brightness is not None:
            await self.send(lights, brightness, 0)

    async def cancel_targets(self, lights: tuple[str, ...]) -> None:
        """Refresh from HA after an explicit button action on these lights."""
        tasks = []
        for selected, target in self.targets.items():
            if set(selected).intersection(lights):
                target.brightness = None
                if target.task:
                    target.task.cancel()
                    tasks.append(target.task)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, lights: tuple[str, ...], target: Target) -> None:
        try:
            while target.brightness is not None:
                revision = target.revision
                started = self.clock()
                target.command_start_brightness = self._current_command_brightness(target, started)
                target.command_target_brightness = target.brightness
                target.command_started = started
                target.command_transition = target.transition
                await self.send(lights, target.brightness, target.transition)
                await asyncio.sleep(max(0, self.command_interval - (self.clock() - started)))
                if target.revision == revision:
                    return
        except asyncio.CancelledError:
            raise
        except Exception:
            target.brightness = None
            _LOGGER.warning("Light command failed; next rotation will resynchronize", exc_info=True)
        finally:
            if target.task is asyncio.current_task():
                target.task = None

    @staticmethod
    def _current_command_brightness(target: Target, now: float) -> float | None:
        start = target.command_start_brightness
        end = target.command_target_brightness
        if start is None or end is None:
            return target.brightness
        if target.command_transition <= 0:
            return end
        progress = max(0.0, min(1.0, (now - target.command_started) / target.command_transition))
        return start + (end - start) * progress

    async def close(self) -> None:
        tasks = [target.task for target in self.targets.values() if target.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
