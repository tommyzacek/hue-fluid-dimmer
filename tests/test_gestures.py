"""Replay physical Tap Dial sequences, including delayed SSE batches."""

import asyncio
from unittest.mock import Mock

import pytest

from custom_components.hue_fluid_dimmer.gestures import BATCH_GRACE, CLICK_WINDOW, Gestures


@pytest.fixture
async def recognition(monkeypatch):
    actions = {"short": ["light.a"]}
    emitted, timers = [], []

    def later(delay, fn, *args):
        timer = Mock()
        timer.delay, timer.fire = delay, lambda: fn(*args)
        timers.append(timer)
        return timer

    monkeypatch.setattr(asyncio.get_running_loop(), "call_later", later)
    holds = []
    engine = Gestures(
        lambda *args: actions,
        lambda *args: emitted.append(args),
        hold_event=lambda *args: holds.append(args),
    )
    return engine, actions, emitted, timers, holds


async def test_short_only_has_no_timer_even_with_long_enabled(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions["long"] = ["scene.a"]
    engine.feed("dial", 2, "initial_press", 10)
    engine.feed("dial", 2, "short_release", 10.078)
    assert emitted == [("dial", 2, "short")]
    assert not timers


async def test_physical_double_batch_emits_only_double(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions["double"] = ["scene.a"]
    for event, updated in [
        ("initial_press", 51.058),
        ("short_release", 51.135),
        ("initial_press", 51.211),
        ("short_release", 51.352),
    ]:
        engine.feed("dial", 2, event, updated)
    assert emitted == [("dial", 2, "double")]
    assert timers[0].cancel.called
    assert timers[0].delay == CLICK_WINDOW + BATCH_GRACE


async def test_physical_triple_batch_suppresses_short_and_double(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions.update(double=["light.b"], triple=["script.a"])
    for initial, released in [(59.210, 59.282), (59.411, 59.486), (59.620, 59.693)]:
        engine.feed("dial", 2, "initial_press", initial)
        engine.feed("dial", 2, "short_release", released)
    assert emitted == [("dial", 2, "triple")]
    assert len(timers) == 2 and all(t.cancel.called for t in timers)


async def test_pending_single_and_double_wait_only_when_needed(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions.update(double=["light.b"], triple=["light.c"])
    engine.feed("dial", 2, "initial_press", 1)
    engine.feed("dial", 2, "short_release", 1.08)
    assert not emitted
    timers[-1].fire()
    assert emitted == [("dial", 2, "short")]
    engine.feed("dial", 2, "initial_press", 2)
    engine.feed("dial", 2, "short_release", 2.08)
    engine.feed("dial", 2, "initial_press", 2.2)
    engine.feed("dial", 2, "short_release", 2.28)
    assert emitted == [("dial", 2, "short")]
    timers[-1].fire()
    assert emitted[-1] == ("dial", 2, "double")


async def test_separate_clicks_in_same_delivery_do_not_become_double(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions["double"] = ["scene.a"]
    for initial in (1, 2):
        engine.feed("dial", 2, "initial_press", initial)
        engine.feed("dial", 2, "short_release", initial + 0.08)
    assert emitted == [("dial", 2, "short")]
    timers[-1].fire()
    assert emitted == [("dial", 2, "short"), ("dial", 2, "short")]


async def test_long_runs_once_without_release_or_repeat_action(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions["long"] = ["scene.a"]
    for event, updated in [
        ("initial_press", 41.789),
        ("long_press", 42.597),
        ("repeat", 42.611),
        ("repeat", 42.9),
        ("long_release", 43.168),
    ]:
        engine.feed("dial", 2, event, updated)
    assert emitted == [("dial", 2, "long")]
    assert not timers


async def test_duplicate_old_and_unarmed_reports_do_nothing(recognition):
    engine, actions, emitted, timers, _ = recognition
    engine.feed("dial", 2, "short_release", 1)
    engine.feed("dial", 2, "long_press", 1.1)
    engine.feed("dial", 2, "initial_press", 2)
    engine.feed("dial", 2, "short_release", 2.1)
    engine.feed("dial", 2, "initial_press", 2)
    engine.feed("dial", 2, "short_release", 2.1)
    assert emitted == [("dial", 2, "short")]


async def test_disabled_action_cannot_fire_from_pending_timer(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions["double"] = ["scene.a"]
    engine.feed("dial", 2, "initial_press", 1)
    engine.feed("dial", 2, "short_release", 1.08)
    del actions["short"]
    timers[-1].fire()
    assert not emitted


async def test_disconnect_or_unload_cancels_pending_and_requires_new_press(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions.update(double=["scene.a"], long=["script.a"])
    engine.feed("dial", 2, "initial_press", 1)
    engine.feed("dial", 2, "short_release", 1.08)
    engine.cancel()
    assert timers[-1].cancel.called and not engine.pending
    timers[-1].fire()
    engine.feed("dial", 2, "short_release", 1.3)
    engine.feed("dial", 2, "long_press", 1.4)
    assert not emitted


async def test_long_second_press_completes_previous_short(recognition):
    engine, actions, emitted, timers, _ = recognition
    actions.update(double=["scene.a"], long=["script.a"])
    engine.feed("dial", 2, "initial_press", 1)
    engine.feed("dial", 2, "short_release", 1.08)
    engine.feed("dial", 2, "initial_press", 1.2)
    engine.feed("dial", 2, "long_press", 2)
    engine.feed("dial", 2, "long_release", 2.5)
    assert emitted == [("dial", 2, "short"), ("dial", 2, "long")]


async def test_dimming_mode_tracks_hold_repeats_and_release(recognition):
    engine, actions, emitted, _, holds = recognition
    actions.update(long=["light.a"], long_mode="dimming")
    for event, updated in [
        ("initial_press", 1.0),
        ("long_press", 1.8),
        ("repeat", 2.6),
        ("repeat", 3.0),
        ("long_release", 3.2),
    ]:
        assert engine.feed("dial", 2, event, updated)
    assert emitted == []
    assert holds == [
        ("dial", 2, "start", 1.8),
        ("dial", 2, "repeat", 2.6),
        ("dial", 2, "repeat", 3.0),
        ("dial", 2, "release", 3.2),
    ]
