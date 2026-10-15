from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.hue_fluid_dimmer import motion
from custom_components.hue_fluid_dimmer.motion import DEFAULTS, MotionLighting
from custom_components.hue_fluid_dimmer.motion_targets import expand_targets, hue_group_members


def setup(policy=None, on=False):
    states = {
        f"light.{x}": SimpleNamespace(
            state="on" if on else "off",
            attributes={"brightness": 153, "color_mode": "color_temp", "color_temp_kelvin": 2700},
        )
        for x in ("a", "b")
    }
    call = AsyncMock()
    hass = SimpleNamespace(
        states=SimpleNamespace(get=states.get), services=SimpleNamespace(async_call=call)
    )
    engine = MotionLighting(
        hass,
        lambda coro: None,
        SimpleNamespace(pause=AsyncMock(return_value=[]), release=AsyncMock()),
    )
    binding = {
        **DEFAULTS,
        "enabled": True,
        "motion_targets": ["light.a", "light.b"],
        "motion_behavior": policy or {},
    }
    return engine, states, call, binding


@pytest.mark.parametrize("arrival,count", [("apply", 1), ("keep", 0)])
async def test_arrival_adopts_on_lights_with_optional_startup_command(arrival, count):
    engine, states, call, binding = setup({"arrival": arrival}, True)
    await engine.update("r", binding, True)
    assert engine.sessions["r"]["lights"] == {"light.a", "light.b"}
    assert call.await_count == count
    await engine.update("r", binding, True)
    assert call.await_count == count


@pytest.mark.parametrize(
    "departure,off,restore",
    [("off", True, False), ("keep", False, False), ("restore", False, True)],
)
async def test_departure_policy_for_originally_on_lights(monkeypatch, departure, off, restore):
    engine, states, call, binding = setup({"departure": departure}, True)
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    session["occupied"] = False
    call.reset_mock()
    monkeypatch.setattr(motion.asyncio, "sleep", AsyncMock())
    await engine.countdown("r", session)
    assert any(c.args[1] == "turn_off" for c in call.await_args_list) == off
    assert (
        any(
            c.args[1] == "turn_on" and c.args[2].get("color_temp_kelvin") == 2700
            for c in call.await_args_list
        )
        == restore
    )
    if departure == "keep":
        call.assert_not_awaited()


async def test_mixed_original_and_off_lights_are_timed_independently(monkeypatch):
    engine, states, call, binding = setup({"arrival": "keep", "departure": "keep"}, True)
    states["light.b"].state = "off"
    await engine.update("r", binding, True)
    assert call.await_args.args[2]["entity_id"] == ["light.b"]
    states["light.b"].state = "on"
    session = engine.sessions["r"]
    session["occupied"] = False
    monkeypatch.setattr(motion.asyncio, "sleep", AsyncMock())
    await engine.countdown("r", session)
    assert call.await_args.args[2]["entity_id"] == ["light.b"]


async def test_default_manual_change_does_not_cancel_timer_or_reapply_startup(monkeypatch):
    engine, states, call, binding = setup()
    await engine.update("r", binding, True)
    for state in states.values():
        state.state = "on"
        state.attributes["brightness"] = 153
    engine.manual_action(["light.a"])
    await engine.update("r", binding, True)
    assert call.await_count == 1
    session = engine.sessions["r"]
    session["occupied"] = False
    monkeypatch.setattr(motion.asyncio, "sleep", AsyncMock())
    await engine.countdown("r", session)
    half = [c.args[2] for c in call.await_args_list if "brightness" in c.args[2]]
    assert all(d["brightness"] == 76 for d in half)
    assert call.await_args.args[1] == "turn_off"


@pytest.mark.parametrize("scope,remaining", [("touched", {"light.b"}), ("all", set())])
async def test_handover_scope_does_not_touch_unselected_lights(scope, remaining):
    engine, states, call, binding = setup({"manual_change": "handover", "manual_scope": scope})
    await engine.update("r", binding, True)
    for state in states.values():
        state.state = "on"
    engine.manual_action(["light.a"])
    assert engine.sessions["r"]["lights"] == remaining
    await engine.update("r", binding, True)
    assert engine.sessions["r"]["lights"] == remaining
    assert call.await_count == 1


async def test_handover_returns_after_off_then_new_motion():
    engine, states, call, binding = setup({"manual_change": "handover"})
    await engine.update("r", binding, True)
    states["light.a"].state = "on"
    engine.manual_action(["light.a"])
    states["light.a"].state = "off"
    engine.light_state("light.a", "off")
    await engine.update("r", binding, True)
    assert "light.a" in engine.sessions["r"]["lights"]
    assert call.await_args.args[2]["entity_id"] == ["light.a"]


async def test_idle_return_requires_absence_and_subsequent_motion():
    engine, states, call, binding = setup(
        {"manual_change": "handover", "return": "idle", "return_seconds": 60}
    )
    now = [0]
    engine.clock = lambda: now[0]
    await engine.update("r", binding, True)
    states["light.a"].state = "on"
    engine.manual_action(["light.a"])
    engine.release_overrides("r", False)
    now[0] = 59
    assert engine.release_overrides("r", True) == {"light.a"}
    engine.release_overrides("r", False)
    now[0] = 120
    await engine.update("r", binding, True)
    assert "light.a" in engine.sessions["r"]["lights"]


@pytest.mark.parametrize("manual_off,restored", [("hold", False), ("resume", True)])
async def test_manual_off_policy(manual_off, restored):
    engine, states, call, binding = setup({"manual_off": manual_off})
    await engine.update("r", binding, True)
    states["light.a"].state = "off"
    engine.manual_action(["light.a"], off=True)
    await engine.update("r", binding, True)
    assert ("light.a" in engine.sessions["r"]["lights"]) == restored


async def test_handover_during_warning_never_restores_or_switches_off_affected_light(monkeypatch):
    engine, states, call, binding = setup({"manual_change": "handover"})
    await engine.update("r", binding, True)
    for state in states.values():
        state.state = "on"
    session = engine.sessions["r"]
    session["occupied"] = False
    count = 0

    async def sleep(delay):
        nonlocal count
        count += 1
        if count == 2:
            engine.manual_action(["light.a"])
            await engine.update("r", binding, True)

    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    await engine.countdown("r", session)
    restores = [
        c.args[2]["entity_id"]
        for c in call.await_args_list
        if c.args[2].get("transition") == 0.5 and "brightness" in c.args[2]
    ]
    assert restores == [["light.b"]]
    assert all(c.args[1] != "turn_off" for c in call.await_args_list)


def test_hue_room_and_nested_ha_group_resolve_same_leaf_entities():
    devices = [
        {"id": "device-a", "services": [{"rtype": "light", "rid": "a"}]},
        {"id": "device-b", "services": [{"rtype": "light", "rid": "b"}]},
    ]
    groups = [
        {
            "id": "room",
            "services": [{"rtype": "grouped_light", "rid": "group"}],
            "children": [
                {"rtype": "device", "rid": "device-a"},
                {"rtype": "device", "rid": "device-b"},
            ],
        }
    ]
    mapping = hue_group_members(
        devices, groups, {"a": "light.a", "b": "light.b", "group": "light.room"}
    )
    states = {"light.nested": SimpleNamespace(attributes={"entity_id": ["light.room", "light.a"]})}
    hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
    assert expand_targets(hass, ["light.nested"], mapping) == {"light.a", "light.b"}


async def test_ending_uses_current_60_percent_not_initial_100_percent(monkeypatch):
    engine, states, call, binding = setup()
    binding["motion_start"] = {"brightness": "configured", "percentage": 100}
    engine.adaptive.mark = AsyncMock()
    await engine.update("r", binding, True)
    for state in states.values():
        state.state = "on"
        state.attributes["brightness"] = 153
    await engine.update("r", binding, True)
    assert call.await_count == 1  # Identical startup commands are batched.
    session = engine.sessions["r"]
    session["occupied"] = False
    monkeypatch.setattr(motion.asyncio, "sleep", AsyncMock())
    await engine.countdown("r", session)
    half = [c.args[2]["brightness"] for c in call.await_args_list if "brightness" in c.args[2]]
    assert half == [76, 76]


async def test_manual_controller_flag_is_not_released_by_old_motion_lease():
    engine, states, call, binding = setup()
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    session["leases"] = [("switch.al", ["light.a", "light.b"], False)]
    engine.manual_action(["light.a"])
    assert session["leases"] == [("switch.al", ["light.b"], False)]


async def test_return_does_not_reclassify_originally_off_light():
    engine, states, call, binding = setup(
        {"manual_change": "handover", "return": "idle", "departure": "keep"}
    )
    await engine.update("r", binding, True)
    states["light.a"].state = "on"
    engine.manual_action(["light.a"])
    engine.overrides["r"]["light.a"]["deadline"] = 0
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    assert "light.a" not in session["initial"]
    assert "light.a" in engine.ending_targets(session)


async def test_movement_during_final_off_starts_new_cycle(monkeypatch):
    import asyncio

    engine, states, call, binding = setup()
    binding["motion_soft_end"] = False
    await engine.update("r", binding, True)
    old = engine.sessions["r"]
    old["occupied"] = False
    pending = []

    async def command(domain, service, data, **kwargs):
        if service == "turn_off":
            pending.append(asyncio.create_task(engine.update("r", binding, True)))

    call.side_effect = command
    monkeypatch.setattr(motion.asyncio, "sleep", AsyncMock())
    await engine.countdown("r", old)
    await asyncio.gather(*pending)
    assert engine.sessions["r"] is not old
    assert engine.sessions["r"]["occupied"]


async def test_bright_room_tracks_on_lights_without_startup_commands():
    engine, states, call, binding = setup()
    states["light.a"].state = "on"
    states["sensor.lux"] = SimpleNamespace(state="200")
    binding.update(motion_use_lux=True, motion_lux=50, motion_lux_entity="sensor.lux")
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    assert session["lights"] == {"light.a"}
    assert engine.ending_targets(session) == {"light.a"}
    call.assert_not_awaited()


@pytest.mark.parametrize("mode", ["half", "fade"])
async def test_group_handover_stops_collateral_ramp(mode):
    import asyncio

    engine, states, call, binding = setup(
        {"manual_scope": "all", "manual_change": "handover"}, True
    )
    engine.create_task = asyncio.create_task
    binding["motion_end_mode"] = mode
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    session.update(
        warning=True, snapshot={"light.a": 153, "light.b": 153}, ramp_started=0, ramp_duration=30
    )
    engine.clock = lambda: 15
    engine.stop_ramps = AsyncMock()
    engine.manual_action(["light.a"])
    await asyncio.gather(*engine.tasks)
    expected = 76 if mode == "fade" else 115
    engine.stop_ramps.assert_awaited_once_with({"light.b": expected})
    assert not session["lights"]


async def test_whole_scope_continue_keeps_collateral_restore_snapshot():
    engine, states, call, binding = setup({"manual_scope": "all"}, True)
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    session["snapshot"] = {"light.a": 153, "light.b": 153}
    engine.manual_action(["light.a"])
    assert session["snapshot"] == {"light.b": 153}


async def test_disabling_one_motion_keeps_other_session():
    engine, states, call, binding = setup()
    await engine.update("r", binding, True)
    await engine.update("other", binding, True)
    await engine.disable("r")
    assert "r" not in engine.sessions
    assert engine.sessions["other"]["occupied"]


async def test_quick_half_takes_two_seconds_but_waits_until_timeout(monkeypatch):
    from custom_components.hue_fluid_dimmer.motion import parse_motion

    engine, states, call, binding = setup(on=True)
    binding.update(motion_timeout=60, motion_end_mode="half_quick")
    assert parse_motion(binding)[1] is None
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    session["occupied"] = False
    sleep = AsyncMock()
    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    call.reset_mock()
    await engine.countdown("r", session)
    assert [c.args[0] for c in sleep.await_args_list] == [30, 30]
    dimming = [c.args[2] for c in call.await_args_list if c.args[1] == "turn_on"]
    assert len(dimming) == 2
    assert all(d["transition"] == 2 and d["brightness"] == 76 for d in dimming)
    assert call.await_args.args[1] == "turn_off"
    assert call.await_args.args[2]["transition"] == 2
