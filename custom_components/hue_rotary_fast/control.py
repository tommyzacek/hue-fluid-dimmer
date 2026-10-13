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
    transition: float = 1
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
        target.brightness = max(
            0, min(100, target.brightness + steps / 15 * binding.get("sensitivity", 1.5))
        )
        target.last_motion = now
        target.transition = binding.get("transition", 1.0)
        target.revision += 1
        if target.task is None:
            target.task = self.create_task(self._run(lights, target))

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

    async def close(self) -> None:
        tasks = [target.task for target in self.targets.values() if target.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
