"""Replay measured REST/SSE timing without device identifiers or absolute times."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from test_runtime import make_runtime


def button(event, updated):
    return {
        "id": "button-a",
        "type": "button",
        "owner": {"rid": "owner-a"},
        "metadata": {"control_id": 1},
        "button": {
            "button_report": {
                "event": event,
                "updated": datetime.fromtimestamp(updated, UTC).isoformat(),
            }
        },
    }


@pytest.fixture
async def runtime_clock(monkeypatch, resource):
    clock = [0.0]
    actions = {
        "short": ["light.a"],
        "double": ["light.b"],
        "triple": ["light.c"],
        "long": ["light.d"],
    }
    runtime, _ = make_runtime(
        monkeypatch, {"controllers": {"dial-a": {"enabled": True, "button_1": actions}}}
    )
    runtime.resources = [resource()]
    runtime.map_buttons([button("initial_press", 0)])
    monkeypatch.setattr(
        "custom_components.hue_fluid_dimmer.runtime.time",
        SimpleNamespace(monotonic=lambda: clock[0]),
    )
    monkeypatch.setattr(asyncio.get_running_loop(), "call_later", lambda *args: Mock())
    emitted = []
    runtime.gestures.emit = lambda *args: emitted.append((*args, clock[0]))
    yield runtime, clock, emitted
    await runtime.close()


def sse(runtime, event, updated):
    runtime.consume_buttons([{"type": "update", "data": [button(event, updated)]}])


def delayed_sse(runtime, event, updated, created):
    runtime.consume_buttons(
        [
            {
                "type": "update",
                "creationtime": datetime.fromtimestamp(created, UTC).isoformat(),
                "data": [button(event, updated)],
            }
        ]
    )


async def test_confirmed_quiet_time_removes_delivery_grace(runtime_clock):
    runtime, clock, emitted = runtime_clock
    sse(runtime, "initial_press", 1)
    clock[0] = 0.1
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    clock[0] = 0.5
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    assert emitted == [("dial-a", 1, "short", 0.5)]
    clock[0] = 1
    sse(runtime, "short_release", 1.08)
    assert emitted == [("dial-a", 1, "short", 0.5)]
    assert not runtime.gestures.pending


async def test_delayed_sse_uses_bridge_creation_time_after_rest_confirmation(runtime_clock):
    runtime, clock, emitted = runtime_clock
    delayed_sse(runtime, "initial_press", 1, 2)
    delayed_sse(runtime, "short_release", 1.08, 2)
    clock[0] = 0.05
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    assert emitted == [("dial-a", 1, "short", 0.05)]


async def test_newer_rest_report_holds_expiry_until_sse_catches_up(runtime_clock):
    runtime, clock, emitted = runtime_clock
    sse(runtime, "initial_press", 1)
    sse(runtime, "short_release", 1.08)
    clock[0] = 0.2
    runtime.consume_button_snapshots([button("short_release", 1.3)])  # Poll missed second initial.
    clock[0] = 1.4
    runtime.gestures.finish(("dial-a", 1))
    assert not emitted
    sse(runtime, "initial_press", 1.2)
    sse(runtime, "short_release", 1.3)
    runtime.consume_button_snapshots([button("short_release", 1.3)])
    assert [row[2] for row in emitted] == ["double"]


async def test_rest_gap_blocks_later_release_until_sse_fills_it(runtime_clock):
    runtime, clock, emitted = runtime_clock
    sse(runtime, "initial_press", 1)
    clock[0] = 0.1
    runtime.consume_button_snapshots([button("initial_press", 1.2)])  # Missed release 1.
    clock[0] = 0.2
    runtime.consume_button_snapshots([button("short_release", 1.3)])
    clock[0] = 0.7
    runtime.consume_button_snapshots([button("short_release", 1.3)])
    assert not emitted
    assert runtime.button_gaps == {("dial-a", 1): 1.3}
    sse(runtime, "short_release", 1.1)
    sse(runtime, "initial_press", 1.2)
    sse(runtime, "short_release", 1.3)
    assert not runtime.button_gaps
    assert [row[2] for row in emitted] == ["double"]


async def test_rest_can_complete_full_triple_before_sse_batch(runtime_clock):
    runtime, clock, emitted = runtime_clock
    for event, updated, observed in [
        ("initial_press", 1, 0.0),
        ("short_release", 1.08, 0.1),
        ("initial_press", 1.2, 0.2),
        ("short_release", 1.28, 0.3),
        ("initial_press", 1.4, 0.4),
        ("short_release", 1.48, 0.5),
    ]:
        clock[0] = observed
        runtime.consume_button_snapshots([button(event, updated)])
    assert [row[2] for row in emitted] == ["triple"]
    assert emitted[0][3] == 0.5


async def test_repeated_snapshot_is_not_a_second_click(runtime_clock):
    runtime, clock, emitted = runtime_clock
    sse(runtime, "initial_press", 1)
    sse(runtime, "short_release", 1.08)
    for t in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        clock[0] = t
        runtime.consume_button_snapshots([button("short_release", 1.08)])
    assert [row[2] for row in emitted] == ["short"]


async def test_rest_duplicate_after_sse_does_not_open_gap(runtime_clock):
    runtime, clock, emitted = runtime_clock
    sse(runtime, "initial_press", 1)
    clock[0] = 0.05
    runtime.consume_button_snapshots([button("initial_press", 1)])
    assert not runtime.button_gaps
    clock[0] = 0.1
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    clock[0] = 0.5
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    assert [row[2] for row in emitted] == ["short"]


async def test_orphan_release_does_not_keep_active_polling_awake(runtime_clock):
    runtime, clock, emitted = runtime_clock
    sse(runtime, "short_release", 1)
    assert not runtime.gestures.pending and not emitted


async def test_rest_orphan_release_recovers_one_click(runtime_clock):
    runtime, clock, emitted = runtime_clock
    clock[0] = 0.1
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    clock[0] = 0.46
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    assert [row[2] for row in emitted] == ["short"]
    assert not runtime.button_gaps


async def test_rest_long_press_emits_without_waiting_for_sse(runtime_clock):
    runtime, clock, emitted = runtime_clock
    for event, updated, observed in [
        ("initial_press", 1.0, 0.0),
        ("long_press", 1.8, 0.8),
        ("repeat", 1.81, 0.81),
        ("long_release", 2.2, 1.2),
    ]:
        clock[0] = observed
        runtime.consume_button_snapshots([button(event, updated)])
    assert emitted == [("dial-a", 1, "long", 0.8)]
    assert not runtime.button_gaps
    assert not runtime.gestures.pending


async def test_rest_repeats_advance_long_dimming_on_bridge_cadence(runtime_clock):
    runtime, clock, _ = runtime_clock
    runtime.entry.subentries["dial-a"].data["button_1"].update(long_mode="dimming")
    runtime.hue_dimming_resources = lambda lights: ()
    steps = []
    runtime.dimmer.button_step = lambda lights, direction, transition, step: steps.append(
        (lights, direction, transition, step)
    )
    sse(runtime, "initial_press", 1.0)
    for event, updated, observed in [
        ("long_press", 1.8, 0.8),
        ("repeat", 1.81, 0.81),  # Hue's immediate confirmation repeat is ignored.
        ("repeat", 2.61, 1.61),
    ]:
        clock[0] = observed
        runtime.consume_button_snapshots([button(event, updated)])
    assert steps == [
        (("light.d",), "up", 0.8, 10.0),
        (("light.d",), "up", pytest.approx(0.92), 10.0),
    ]
    assert not runtime.button_gaps


async def test_native_hue_ramp_reverses_after_one_endpoint_repeat(runtime_clock):
    runtime, _, _ = runtime_clock
    runtime.entry.subentries["dial-a"].data["button_1"].update(long_mode="dimming")
    runtime.hue_dimming_resources = lambda lights: (("grouped_light", "group-id"),)
    runtime.read_brightness = lambda lights: 100.0  # HA still shows the old transition target.
    runtime.client.read_brightness = AsyncMock(return_value=95.0)
    commands = []

    async def delta(resource_type, resource_id, brightness_delta, duration_ms):
        commands.append((resource_type, resource_id, brightness_delta, duration_ms))

    runtime.client.brightness_delta = delta
    runtime.client.brightness_transition = AsyncMock()
    runtime.client.stop_dimming = AsyncMock()
    runtime.button_hold_event("dial-a", 1, "start", 1.8)
    await asyncio.sleep(0)
    await asyncio.gather(*tuple(runtime.action_tasks))
    assert commands == [("grouped_light", "group-id", 5.0, 800)]
    assert runtime.button_ramp_states[("dial-a", 1)]["brightness"] == 100.0

    runtime.button_hold_event("dial-a", 1, "repeat", 1.81)
    runtime.button_hold_event("dial-a", 1, "repeat", 2.6)
    assert runtime.button_ramp_states[("dial-a", 1)]["skip_endpoint_repeat"]
    assert len(commands) == 1

    runtime.button_hold_event("dial-a", 1, "repeat", 3.4)
    await asyncio.sleep(0)
    await asyncio.gather(*tuple(runtime.action_tasks))
    assert commands[-1] == ("grouped_light", "group-id", -10.0, 800)
    assert runtime.button_ramp_states[("dial-a", 1)]["direction"] == "down"

    runtime.button_hold_event("dial-a", 1, "release", 3.5)
    await asyncio.gather(*tuple(runtime.action_tasks))
    runtime.client.stop_dimming.assert_awaited_once_with("grouped_light", "group-id")
    assert ("dial-a", 1) not in runtime.button_ramp_states


async def test_orphan_rest_long_press_opens_gap(runtime_clock):
    runtime, clock, emitted = runtime_clock
    clock[0] = 0.8
    runtime.consume_button_snapshots([button("long_press", 1.8)])
    assert not emitted
    assert runtime.button_gaps == {("dial-a", 1): 1.8}


@pytest.mark.parametrize("missed", [False, True])
async def test_measured_six_pairs_with_missed_rest_transitions(runtime_clock, missed):
    runtime, clock, emitted = runtime_clock
    fixture = json.loads(Path(__file__).with_name("rest_sse_timings.json").read_text())
    rest = fixture["rest_changes"]
    if missed:
        rest = [r for r in rest if r[1] == "short_release"]
    events = [(r[0], "rest", r[1], r[2]) for r in rest]
    events += [(r[0], "sse", r[1], r[2]) for r in fixture["sse_reports"]]
    # Repeated queries establish observed quiet time; no invented transitions.
    for i in range(1, 401):
        t = i / 10
        known = [r for r in rest if r[0] <= t]
        if known:
            r = known[-1]
            events.append((t, "rest", r[1], r[2]))
    frames = {}
    for t, source, event, updated in events:
        frames.setdefault((t, source), []).append(button(event, updated + 100))
    for (t, source), items in sorted(frames.items()):
        clock[0] = t
        if source == "rest":
            runtime.consume_button_snapshots(items)
        else:
            runtime.consume_buttons([{"type": "update", "data": items}])
    assert [row[2] for row in emitted] == [
        "double",
        "double",
        "short",
        "short",
        "double",
        "short",
        "short",
        "short",
        "short",
    ]
    assert not runtime.gestures.pending


@pytest.mark.parametrize("gap, expected", [(0.349, "double"), (0.351, "short")])
async def test_350_ms_gap_boundary(runtime_clock, gap, expected):
    runtime, clock, emitted = runtime_clock
    runtime.consume_buttons(
        [
            {
                "type": "update",
                "data": [
                    button("initial_press", 1),
                    button("short_release", 1.1),
                    button("initial_press", 1.1 + gap),
                    button("short_release", 1.2 + gap),
                ],
            }
        ]
    )
    clock[0] = 0.1
    runtime.consume_button_snapshots([button("short_release", 1.2 + gap)])
    clock[0] = 0.6
    runtime.consume_button_snapshots([button("short_release", 1.2 + gap)])
    assert [row[2] for row in emitted] == (
        [expected] if expected == "double" else ["short", "short"]
    )


async def test_active_button_polling_sleeps_until_wake_and_stops(monkeypatch, resource):
    runtime, _ = make_runtime(monkeypatch, {"poll_interval": 0.01, "active_window": 0.02})
    runtime.resources = [resource()]
    calls = []

    async def fetch():
        calls.append(1)
        return []

    runtime.client.button_resources = fetch
    runtime.button_poll_task = asyncio.create_task(runtime.poll_buttons())
    await asyncio.sleep(0.02)
    assert not calls
    runtime.wake_buttons()
    await asyncio.sleep(0.05)
    count = len(calls)
    assert count >= 1
    await asyncio.sleep(0.02)
    assert len(calls) == count
    await runtime.close()
    assert runtime.button_poll_task.done()


async def test_continuous_button_polling_is_one_bridge_batch(monkeypatch, resource):
    runtime, _ = make_runtime(monkeypatch, {"polling_mode": "continuous", "poll_interval": 0.01})
    runtime.resources = [resource(resource_id=f"dial-{i}") for i in range(100)]
    calls = []

    async def fetch():
        calls.append(1)
        return []

    runtime.client.button_resources = fetch
    runtime.button_poll_task = asyncio.create_task(runtime.poll_buttons())
    await asyncio.sleep(0.035)
    await runtime.close()
    assert 2 <= len(calls) <= 5


async def test_slow_query_cannot_prove_quiet_time_after_its_start(runtime_clock):
    runtime, clock, emitted = runtime_clock
    sse(runtime, "initial_press", 1)
    sse(runtime, "short_release", 1.08)
    clock[0] = 0.1
    runtime.consume_button_snapshots([button("short_release", 1.08)], checked_at=0.05)
    clock[0] = 0.8
    runtime.consume_button_snapshots([button("short_release", 1.08)], checked_at=0.2)
    assert not emitted  # A slow response may contain a snapshot from before the deadline.
    clock[0] = 0.9
    runtime.consume_button_snapshots([button("short_release", 1.08)], checked_at=0.85)
    assert [row[2] for row in emitted] == ["short"]


async def test_next_query_starts_at_quiet_time_deadline(runtime_clock):
    runtime, clock, _ = runtime_clock
    sse(runtime, "initial_press", 1)
    clock[0] = 0.1
    runtime.consume_button_snapshots([button("short_release", 1.08)])
    clock[0] = 0.44
    delay = runtime.button_poll_delay(0.1, started=0.4)
    assert delay == pytest.approx(0.011)
