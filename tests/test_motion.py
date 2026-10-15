from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.hue_fluid_dimmer import motion
from custom_components.hue_fluid_dimmer.config_flow import MotionTimeout, binding_schema
from custom_components.hue_fluid_dimmer.motion import DEFAULTS, MotionLighting, parse_motion


def manager():
    states = {"light.a": SimpleNamespace(state="off", attributes={"brightness": 153})}
    call = AsyncMock()
    hass = SimpleNamespace(
        states=SimpleNamespace(get=states.get), services=SimpleNamespace(async_call=call)
    )
    adaptive = SimpleNamespace(pause=AsyncMock(return_value=[]), release=AsyncMock())
    return MotionLighting(hass, lambda coro: None, adaptive), states, call


def test_motion_rejects_unknown_end_mode():
    assert parse_motion({"motion_end_mode": "invalid"})[1] == "motion_end_invalid"


def test_motion_form_has_no_button_or_dial_fields():
    schema = binding_schema({"controller_kind": "motion"})
    values = schema({})
    assert "dial" not in values and "button_1" not in values
    assert values["enabled"] is False
    assert parse_motion({**values, "enabled": True})[1] == "motion_targets_required"


async def test_default_motion_adopts_already_lit_lights():
    engine, states, call = manager()
    states["light.a"].state = "on"
    await engine.update("sensor", {"enabled": True, "motion_targets": ["light.a"]}, True)
    assert engine.sessions["sensor"]["lights"] == {"light.a"}
    assert call.await_count == 1


async def test_motion_warning_is_half_of_snapshot_then_switches_off(monkeypatch):
    engine, states, call = manager()
    binding = {**DEFAULTS, "enabled": True, "motion_targets": ["light.a"]}
    await engine.update("sensor", binding, True)
    states["light.a"].state = "on"
    session = engine.sessions["sensor"]
    session["occupied"] = False
    sleep = AsyncMock()
    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    await engine.countdown("sensor", session)
    assert [c.args[0] for c in sleep.await_args_list] == [270, 30]
    assert call.await_args_list[1].args[2]["brightness"] == 76
    assert call.await_args_list[1].args[2]["transition"] == 30
    assert call.await_args_list[-1].args[2]["transition"] == 2
    assert call.await_args_list[-1].args[1] == "turn_off"
    assert not engine.sessions


async def test_motion_during_warning_restores_original_not_100_percent(monkeypatch):
    engine, states, call = manager()
    binding = {**DEFAULTS, "enabled": True, "motion_targets": ["light.a"]}
    await engine.update("sensor", binding, True)
    states["light.a"].state = "on"
    session = engine.sessions["sensor"]
    session["occupied"] = False
    count = 0

    async def sleep(delay):
        nonlocal count
        count += 1
        if count == 2:
            await engine.update("sensor", binding, True)

    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    await engine.countdown("sensor", session)
    assert call.await_args_list[-1].args[2]["brightness"] == 153
    assert all(c.args[1] != "turn_off" for c in call.await_args_list)
    assert session["occupied"] and not session["warning"]


async def test_manual_change_cancels_warning_without_restoring_stale_brightness(monkeypatch):
    engine, states, call = manager()
    binding = {
        **DEFAULTS,
        "enabled": True,
        "motion_targets": ["light.a"],
        "motion_behavior": {"manual_change": "handover"},
    }
    await engine.update("sensor", binding, True)
    states["light.a"].state = "on"
    session = engine.sessions["sensor"]
    session["occupied"] = False
    count = 0

    async def sleep(delay):
        nonlocal count
        count += 1
        if count == 2:
            engine.cancel_targets(["light.a"])

    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    await engine.countdown("sensor", session)
    assert not engine.sessions
    assert all(c.args[1] != "turn_off" for c in call.await_args_list)
    assert call.await_count == 2


@pytest.mark.parametrize(
    "lux,activate", [("34", True), ("35", False), ("36", False), ("unavailable", False)]
)
async def test_lux_gate_uses_real_lux_and_strict_threshold(lux, activate):
    engine, states, call = manager()
    states["sensor.lux"] = SimpleNamespace(state=lux, attributes={})
    binding = {
        **DEFAULTS,
        "enabled": True,
        "motion_targets": ["light.a"],
        "motion_use_lux": True,
        "motion_lux": 35,
        "motion_lux_entity": "sensor.lux",
    }
    await engine.update("sensor", binding, True)
    assert bool(engine.sessions) == activate
    assert call.await_count == int(activate)


@pytest.mark.parametrize(
    "slider,limited", [(0, True), (35, True), (650, True), (651, False), (660, False)]
)
def test_single_lux_slider_encodes_threshold_and_unrestricted(slider, limited):
    binding, error = parse_motion({"motion_lux_slider": slider})
    assert error is None
    assert binding["motion_use_lux"] is limited
    if limited:
        assert binding["motion_lux"] == slider
    assert "motion_lux_slider" not in binding


def test_motion_lux_slider_is_always_visible_and_preserves_saved_mode():
    unlimited = binding_schema({"controller_kind": "motion"})({})
    limited = binding_schema(
        {"controller_kind": "motion", "motion_use_lux": True, "motion_lux": 35}
    )({})
    assert "motion_use_lux" not in unlimited
    assert unlimited["motion_lux_slider"] == 660
    assert limited["motion_lux_slider"] == 35
    assert parse_motion(unlimited)[0]["motion_use_lux"] is False


@pytest.mark.parametrize(
    "enabled,limited,activates",
    [("off", True, False), ("unavailable", True, False), ("on", True, True), ("off", False, True)],
)
async def test_disabled_light_sensor_never_uses_stale_lux(enabled, limited, activates):
    engine, states, call = manager()
    states["sensor.lux"] = SimpleNamespace(state="1", attributes={})
    states["switch.lux_enabled"] = SimpleNamespace(state=enabled, attributes={})
    await engine.update(
        "sensor",
        {
            **DEFAULTS,
            "enabled": True,
            "motion_targets": ["light.a"],
            "motion_use_lux": limited,
            "motion_lux": 35,
            "motion_lux_entity": "sensor.lux",
            "motion_lux_enabled_entity": "switch.lux_enabled",
        },
        True,
    )
    assert bool(engine.sessions) is activates
    assert bool(call.await_count) is activates


async def test_full_fade_uses_30_second_native_off_ramp(monkeypatch):
    engine, states, call = manager()
    binding = {
        **DEFAULTS,
        "enabled": True,
        "motion_targets": ["light.a"],
        "motion_end_mode": "fade",
    }
    await engine.update("sensor", binding, True)
    states["light.a"].state = "on"
    session = engine.sessions["sensor"]
    session["occupied"] = False
    sleep = AsyncMock()
    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    await engine.countdown("sensor", session)
    assert [c.args[0] for c in sleep.await_args_list] == [270, 30]
    assert call.await_args_list[1].args[1] == "turn_off"
    assert call.await_args_list[1].args[2]["transition"] == 30
    assert call.await_args_list[-1].args[2]["transition"] == 2


async def test_motion_interrupts_full_fade_despite_optimistic_off_state(monkeypatch):
    engine, states, call = manager()
    binding = {
        **DEFAULTS,
        "enabled": True,
        "motion_targets": ["light.a"],
        "motion_end_mode": "fade",
    }
    await engine.update("sensor", binding, True)
    states["light.a"].state = "on"
    session = engine.sessions["sensor"]
    session["occupied"] = False
    count = 0

    async def sleep(delay):
        nonlocal count
        count += 1
        if count == 2:
            states["light.a"].state = "off"
            await engine.update("sensor", binding, True)

    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    await engine.countdown("sensor", session)
    assert call.await_args_list[-1].args[1] == "turn_on"
    assert call.await_args_list[-1].args[2]["brightness"] == 153
    assert call.await_args_list[-1].args[2]["transition"] == 0.5
    assert len([c for c in call.await_args_list if c.args[1] == "turn_off"]) == 1
    assert session["occupied"]


@pytest.mark.parametrize("total,enabled,waits", [(300, False, [300, 0]), (10, True, [30, 30])])
async def test_soft_end_disabled_and_short_timers(monkeypatch, total, enabled, waits):
    engine, states, call = manager()
    binding = {
        **DEFAULTS,
        "enabled": True,
        "motion_targets": ["light.a"],
        "motion_timeout": total,
        "motion_soft_end": enabled,
    }
    await engine.update("sensor", binding, True)
    states["light.a"].state = "on"
    session = engine.sessions["sensor"]
    session["occupied"] = False
    sleep = AsyncMock()
    monkeypatch.setattr(motion.asyncio, "sleep", sleep)
    await engine.countdown("sensor", session)
    assert [c.args[0] for c in sleep.await_args_list] == waits
    if not enabled:
        assert call.await_count == 2
    else:
        assert call.await_args_list[1].args[2]["transition"] == 30


def test_soft_end_form_removes_detail_fields_and_migrates_old_disabled_warning():
    values = binding_schema({"controller_kind": "motion", "motion_warning": 0})({})
    assert values["motion_soft_end"] is False
    assert not {"motion_warning", "motion_warning_percent", "motion_transition"} & values.keys()
    binding, error = parse_motion({"motion_warning": 0})
    assert error is None and binding["motion_soft_end"] is False


async def test_startup_defaults_do_not_send_brightness_or_color():
    engine, states, call = manager()
    await engine.update(
        "sensor", {**DEFAULTS, "enabled": True, "motion_targets": ["light.a"]}, True
    )
    assert call.await_args.args[2] == {"entity_id": ["light.a"], "transition": 0.5}


async def test_configured_brightness_and_color_mark_both_components():
    engine, states, call = manager()
    engine.adaptive.mark = AsyncMock()
    states["light.a"].attributes["supported_color_modes"] = ["color_temp"]
    states["light.a"].attributes["min_color_temp_kelvin"] = 2200
    await engine.update(
        "sensor",
        {
            **DEFAULTS,
            "enabled": True,
            "motion_targets": ["light.a"],
            "motion_start": {
                "brightness": "configured",
                "percentage": 42,
                "color": "temperature",
                "temperature": 1800,
            },
        },
        True,
    )
    assert call.await_args.args[2]["brightness_pct"] == 42
    assert call.await_args.args[2]["color_temp_kelvin"] == 2200
    engine.adaptive.mark.assert_awaited_once_with(["light.a"], component="both")


def test_legacy_previous_brightness_migrates_to_unchanged():
    binding, error = parse_motion({"motion_start": {"brightness": "previous"}})
    assert error is None
    assert binding["motion_start"]["brightness"] == "unchanged"


async def test_unsupported_color_is_not_sent_to_dimmable_only_light():
    engine, states, call = manager()
    states["light.a"].attributes["supported_color_modes"] = ["brightness"]
    await engine.update(
        "sensor",
        {
            **DEFAULTS,
            "enabled": True,
            "motion_targets": ["light.a"],
            "motion_start": {"color": "rgb", "rgb": [1, 2, 3]},
        },
        True,
    )
    assert call.await_args.args[2] == {"entity_id": ["light.a"], "transition": 0.5}


@pytest.mark.parametrize(
    "options",
    [{"percentage": 101}, {"color": "invalid"}, {"rgb": [256, 0, 0]}, {"temperature": 500}],
)
def test_reject_invalid_startup_settings(options):
    assert parse_motion({"motion_start": options})[1] == "motion_start_invalid"


@pytest.mark.parametrize(
    "value,expected", [(2738, 2700), (2762, 2800), (2750, 2800), (1500, 1500), (10000, 10000)]
)
def test_startup_temperature_snaps_to_nearest_hundred(value, expected):
    binding, error = parse_motion({"motion_start": {"temperature": value}})
    assert error is None and binding["motion_start"]["temperature"] == expected


def test_motion_timeout_minimum_is_one_minute():
    schema = binding_schema({"controller_kind": "motion", "motion_timeout": 10})
    assert schema({})["motion_periods"][0]["timeout"] == 60
    assert MotionTimeout()(60) == 60
    with pytest.raises(Exception, match="too small"):
        MotionTimeout()(59)


def test_motion_timeout_slider_steps_and_position():
    schema = binding_schema({"controller_kind": "motion"})
    fields = [key.schema for key in schema.schema]
    assert "motion_timeout" not in fields
    assert "motion_start" not in fields
    assert "motion_periods" in fields
    assert MotionTimeout()(3600) == 3600
    assert MotionTimeout()(90) == 90
    for invalid in (30, 75, 3601):
        with pytest.raises(Exception):
            MotionTimeout()(invalid)


def test_motion_timeout_uses_minute_steps_above_ten_minutes():
    for valid in (570, 600, 660, 3600):
        assert MotionTimeout()(valid) == valid
    for invalid in (601, 615, 645):
        with pytest.raises(Exception):
            MotionTimeout()(invalid)
    legacy = binding_schema({"controller_kind": "motion", "motion_timeout": 615})
    assert legacy({})["motion_periods"][0]["timeout"] == 600


async def test_presence_gate_blocks_new_cycle_and_unavailable():
    engine, states, call = manager()
    options = {
        "motion_gate_enabled": True,
        "motion_gate_entity": "sensor.house",
        "motion_gate_states": "doma, návštěva",
    }
    engine.gate_options = lambda: options
    binding = {**DEFAULTS, "enabled": True, "motion_targets": ["light.a"]}
    for value in (None, "pryč", "unknown", "unavailable"):
        if value is not None:
            states["sensor.house"] = SimpleNamespace(state=value)
        await engine.update("sensor", binding, True)
        assert not engine.sessions
    call.assert_not_awaited()
    states["sensor.house"] = SimpleNamespace(state="doma")
    await engine.update("sensor", binding, True)
    assert "sensor" in engine.sessions
    assert call.await_count == 1


async def test_presence_gate_finishes_cycle_without_restore_or_timer_extension(monkeypatch):
    import asyncio

    engine, states, call = manager()
    tasks = []
    engine.create_task = lambda coro: tasks.append(asyncio.create_task(coro)) or tasks[-1]
    options = {
        "motion_gate_enabled": True,
        "motion_gate_entity": "sensor.house",
        "motion_gate_states": "doma",
    }
    engine.gate_options = lambda: options
    states["sensor.house"] = SimpleNamespace(state="doma")
    binding = {**DEFAULTS, "enabled": True, "motion_targets": ["light.a"]}
    await engine.update("sensor", binding, True)
    states["light.a"].state = "on"
    session = engine.sessions["sensor"]
    states["sensor.house"].state = "pryč"
    await engine.gate_changed()
    timer = session["timer"]
    assert not session["occupied"]
    session["warning"] = True
    await engine.update("sensor", binding, True)
    await engine.update("sensor", binding, False)
    assert session["warning"] and session["timer"] is timer
    assert call.await_count == 1
    monkeypatch.setattr(motion.asyncio, "sleep", AsyncMock())
    await timer
    assert call.await_args_list[-1].args[1] == "turn_off"
    assert not engine.sessions
