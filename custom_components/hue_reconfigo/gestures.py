"""Timestamp-based button recognition, with no delay for short-only bindings."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

# Gesture interval uses Bridge timestamps. Receipt grace handles its ~1 s SSE batches.
CLICK_WINDOW = 0.35
BATCH_GRACE = 1.0


@dataclass
class Pending:
    count: int = 0
    released: float | None = None
    pressed: bool = False
    held: bool = False
    timer: asyncio.TimerHandle | None = None


class Gestures:
    def __init__(
        self,
        actions: Callable,
        emit: Callable,
        ready: Callable | None = None,
        hold_event: Callable | None = None,
    ) -> None:
        self.actions, self.emit = actions, emit
        self.ready = ready or (lambda key, state: True)
        self.hold_event = hold_event or (lambda *args: None)
        self.pending: dict[tuple[str, int], Pending] = {}
        self.latest: dict[tuple[str, int], float] = {}

    def cancel(self) -> None:
        for state in self.pending.values():
            if state.timer:
                state.timer.cancel()
        self.pending.clear()

    def finish(self, key: tuple[str, int], force: bool = False) -> None:
        state = self.pending.get(key)
        if state is None:
            return
        if state.timer:
            state.timer.cancel()
        if not force and not self.ready(key, state):
            state.timer = asyncio.get_running_loop().call_later(BATCH_GRACE, self.finish, key)
            return
        self.pending.pop(key, None)
        action = {1: "short", 2: "double", 3: "triple"}.get(state.count)
        if action and self.actions(*key).get(action):
            self.emit(*key, action)

    def feed(self, resource: str, index: int, event: str, updated: float) -> bool:
        key = resource, index
        if updated <= self.latest.get(key, float("-inf")):
            return False
        actions = self.actions(*key)
        if not actions:
            state = self.pending.pop(key, None)
            if state and state.timer:
                state.timer.cancel()
            return False
        state = self.pending.get(key)
        if state is None and event != "initial_press":
            return False
        if state is not None:
            if event == "initial_press" and state.pressed:
                return False
            if event == "short_release" and (not state.pressed or state.held):
                return False
            if event == "long_press" and (not state.pressed or state.held):
                return False
            if event == "long_release" and (not state.pressed or not state.held):
                return False
            if event == "repeat" and (not state.pressed or not state.held):
                return False
        self.latest[key] = updated
        state = self.pending.setdefault(key, Pending())
        if event == "initial_press":
            if state.timer:
                state.timer.cancel()
                state.timer = None
            if state.released is not None and updated - state.released > CLICK_WINDOW:
                self.finish(key, force=True)
                state = self.pending.setdefault(key, Pending())
            state.pressed, state.held = True, False
        elif event == "long_press" and state.pressed and not state.held:
            # A long second press completes the previous short sequence separately.
            self.finish(key, force=True)
            state = self.pending.setdefault(key, Pending(pressed=True))
            state.held = True
            if actions.get("long_mode") == "dimming":
                self.hold_event(*key, "start", updated)
            elif actions.get("long"):
                self.emit(*key, "long")
        elif event == "short_release" and state.pressed and not state.held:
            state.pressed = False
            state.count += 1
            state.released = updated
            maximum = 3 if actions.get("triple") else 2 if actions.get("double") else 1
            if state.count >= maximum:
                self.finish(key, force=True)
            else:
                state.timer = asyncio.get_running_loop().call_later(
                    CLICK_WINDOW + BATCH_GRACE, self.finish, key
                )
        elif event == "repeat" and state.pressed and state.held:
            self.hold_event(*key, "repeat", updated)
        elif event == "long_release":
            # Never turn a held press into an additional short action.
            self.finish(key, force=True)
            if actions.get("long_mode") == "dimming":
                self.hold_event(*key, "release", updated)
        else:
            return False
        return True
