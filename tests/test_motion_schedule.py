import asyncio
import runpy
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from custom_components.hue_fluid_dimmer.config_flow import binding_schema
from custom_components.hue_fluid_dimmer.motion import DEFAULTS, parse_motion
from custom_components.hue_fluid_dimmer.motion_schedule import effective_binding, periods_for

setup = runpy.run_path("tests/test_motion_policies.py")["setup"]


def period(start, **changes):
    return {**periods_for(DEFAULTS)[0], "id": start, "start": start, **changes}


@pytest.mark.parametrize(
    "clock,expected",
    [("07:59", "23:00"), ("08:00", "08:00"), ("22:59", "08:00"), ("23:00", "23:00")],
)
def test_period_boundaries_and_midnight(clock, expected):
    binding = {**DEFAULTS, "motion_periods": [period("23:00"), period("08:00")]}
    assert (
        effective_binding(binding, datetime.fromisoformat("2026-10-15T" + clock))[
            "motion_period_id"
        ]
        == expected
    )


@pytest.mark.parametrize(
    "blocks",
    [
        [],
        [period("08:00"), period("08:00")],
        [period("24:00")],
        [period("08:00", timeout=75)],
        [period("08:00", override_targets=True, targets=[])],
        [period("08:00", targets=["switch.bad"])],
        [period("08:00", startup={"color": "bad"})],
    ],
)
def test_invalid_periods_rejected(blocks):
    assert parse_motion({"motion_periods": blocks})[1] == "motion_periods_invalid"


def test_legacy_form_migrates_startup_and_timeout_without_changing_globals():
    old = {
        **DEFAULTS,
        "controller_kind": "motion",
        "motion_timeout": 120,
        "motion_start": {"brightness": "configured", "percentage": 73},
        "motion_end_mode": "half_quick",
        "motion_behavior": {"arrival": "keep"},
    }
    values = binding_schema(old)({})
    binding, error = parse_motion(values)
    assert not error
    block = binding["motion_periods"][0]
    assert block["startup"]["percentage"] == 73 and block["timeout"] == 120
    assert binding["motion_end_mode"] == "half_quick"
    assert binding["motion_behavior"]["arrival"] == "keep"


async def test_quiet_period_does_not_start_but_running_day_cycle_continues():
    engine, states, call, binding = setup()
    binding["motion_periods"] = [period("08:00", timeout=120), period("23:00", do_not_disturb=True)]
    engine.now = lambda: datetime(2026, 10, 15, 22, 59)
    await engine.update("r", binding, True)
    session = engine.sessions["r"]
    engine.now = lambda: datetime(2026, 10, 15, 23, 1)
    await engine.update("r", binding, True)
    assert engine.sessions["r"] is session and session["binding"]["motion_timeout"] == 120
    await engine.disable("r")
    call.reset_mock()
    await engine.update("r", binding, True)
    assert "r" not in engine.sessions
    call.assert_not_awaited()


async def test_period_targets_and_timer_do_not_mutate_original():
    engine, states, call, binding = setup()
    binding["motion_periods"] = [
        period("00:00", timeout=90, override_targets=True, targets=["light.a"])
    ]
    await engine.update("r", binding, True)
    assert engine.sessions["r"]["lights"] == {"light.a"}
    assert engine.sessions["r"]["binding"]["motion_timeout"] == 90
    assert binding["motion_targets"] == ["light.a", "light.b"]


async def test_previous_brightness_does_not_halve_each_cycle(monkeypatch):
    from custom_components.hue_fluid_dimmer import motion

    engine, states, call, binding = setup()
    engine.adaptive.mark = AsyncMock()
    engine.create_task = asyncio.create_task
    states["light.a"].attributes["brightness"] = 204
    states["light.b"].attributes["brightness"] = 102
    await engine.update("r", binding, True)
    for state in states.values():
        state.state = "on"
    session = engine.sessions["r"]
    session["occupied"] = False
    monkeypatch.setattr(motion.asyncio, "sleep", AsyncMock())
    await engine.countdown("r", session)
    for state in states.values():
        state.state = "off"
        state.attributes["brightness"] //= 2
    call.reset_mock()
    await engine.update("r", binding, True)
    restored = {
        entity: c.args[2]["brightness"]
        for c in call.await_args_list
        for entity in c.args[2]["entity_id"]
    }
    assert restored == {"light.a": 204, "light.b": 102}
    assert not engine.remembered
    engine.adaptive.mark.assert_not_awaited()


async def test_external_turn_on_invalidates_old_brightness_only():
    engine, states, call, binding = setup()
    engine.remembered = {"light.a": {"brightness": 204, "owner": "r"}}
    engine.light_state("light.a", "on", "off")
    assert not engine.remembered
    assert states["light.a"].attributes["color_temp_kelvin"] == 2700


async def test_remembered_brightness_survives_restart_and_disable_clears_it():
    engine, states, call, binding = setup()
    saved = {"format": 2, "levels": {"light.a": {"brightness": 204, "owner": "r"}}}
    store = engine.storage = type("Store", (), {})()
    store.async_load = AsyncMock(return_value=saved)
    store.async_save = AsyncMock()
    engine.create_task = asyncio.create_task
    await engine.load()
    assert engine.remembered["light.a"]["brightness"] == 204
    await engine.disable("r")
    await asyncio.gather(*engine.tasks)
    assert not engine.remembered
    assert store.async_save.await_args.args[0]["levels"] == {}


async def test_failed_on_keeps_previous_brightness_for_retry():
    from homeassistant.exceptions import HomeAssistantError

    engine, states, call, binding = setup()
    engine.remembered = {"light.a": {"brightness": 204, "owner": "r"}}
    call.side_effect = HomeAssistantError("offline")
    await engine.update("r", binding, True)
    assert engine.remembered["light.a"]["brightness"] == 204
    assert "r" not in engine.sessions


async def test_configured_startup_overrides_saved_previous_brightness():
    engine, states, call, binding = setup()
    engine.adaptive.mark = AsyncMock()
    engine.remembered = {"light.a": {"brightness": 204, "owner": "r"}}
    binding["motion_start"] = {"brightness": "configured", "percentage": 35}
    await engine.update("r", binding, True)
    assert all(c.args[2]["brightness_pct"] == 35 for c in call.await_args_list)
    assert not engine.remembered
