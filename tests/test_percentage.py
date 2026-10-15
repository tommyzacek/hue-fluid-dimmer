"""Verify smooth numeric/fan services, endpoint reversal and release cancellation."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.hue_reconfigo.percentage import PercentageRamp


def controller(entity, state, attributes):
    call = AsyncMock()
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda _: SimpleNamespace(state=state, attributes=attributes)),
        services=SimpleNamespace(async_call=call),
    )
    ramp = PercentageRamp(hass, asyncio.create_task, tick=0.005)
    return ramp, call


@pytest.mark.parametrize(
    ("entity", "state", "attributes", "domain", "service", "field", "expected"),
    [
        ("number.pwm", "59", {"min": 0, "max": 100, "step": 1}, "number", "set_value", "value", 69),
        (
            "number.raw",
            "100",
            {"min": 0, "max": 200, "step": 2},
            "number",
            "set_value",
            "value",
            120,
        ),
        (
            "fan.test",
            "on",
            {"percentage": 50, "percentage_step": 1},
            "fan",
            "set_percentage",
            "percentage",
            60,
        ),
    ],
)
async def test_ramp_sends_intermediate_values_and_correct_endpoint(
    entity, state, attributes, domain, service, field, expected
):
    ramp, call = controller(entity, state, attributes)
    ramp.start(("dial", 1), (entity,), 10, 0.03)
    await ramp.ramps[("dial", 1)].task
    values = [c.args[2][field] for c in call.await_args_list]
    assert len(set(values)) > 2
    assert values == sorted(values)
    call.assert_awaited_with(domain, service, {"entity_id": entity, field: expected}, blocking=True)
    await ramp.close()


async def test_release_cancels_worker_without_a_final_target_command():
    ramp, call = controller("number.pwm", "50", {"min": 0, "max": 100, "step": 1})
    ramp.start(("dial", 1), ("number.pwm",), 10, 0.03)
    task = ramp.ramps[("dial", 1)].task
    ramp.stop(("dial", 1))
    await asyncio.gather(task, return_exceptions=True)
    call.assert_not_awaited()
    await ramp.close()


async def test_maximum_stops_without_reversing():
    ramp, _ = controller("number.pwm", "95", {"min": 0, "max": 100, "step": 1})
    key = ("dial", 1)
    ramp.start(key, ("number.pwm",), 10, 0.01)
    await ramp.ramps[key].task
    ramp.advance(key, 10, 0.01)
    assert ramp.ramps[key].goals["number.pwm"] == 100
    ramp.advance(key, 10, 0.01)
    assert ramp.ramps[key].goals["number.pwm"] == 100
    await ramp.ramps[key].task
    await ramp.close()


async def test_number_previous_value_is_persisted_and_restored_after_reload():
    ramp, call = controller("number.pwm", "59", {"min": 0, "max": 100, "step": 1})
    storage = Mock(
        async_save=AsyncMock(), async_load=AsyncMock(return_value={"previous": {"number.pwm": 59}})
    )
    ramp.storage = storage
    await ramp.action("number.pwm", "previous", 100)
    call.assert_awaited_with(
        "number", "set_value", {"entity_id": "number.pwm", "value": 0}, blocking=True
    )
    storage.async_save.assert_awaited_once_with({"previous": {"number.pwm": 59}})
    restored, restored_call = controller("number.pwm", "0", {"min": 0, "max": 100, "step": 1})
    restored.storage = storage
    await restored.load()
    await restored.action("number.pwm", "previous", 100)
    restored_call.assert_awaited_once_with(
        "number", "set_value", {"entity_id": "number.pwm", "value": 59}, blocking=True
    )


@pytest.mark.parametrize(
    ("entity", "state", "attributes", "domain", "service", "field", "value"),
    [
        ("light.test", "off", {}, "light", "turn_on", "brightness_pct", 30),
        ("fan.test", "off", {}, "fan", "set_percentage", "percentage", 30),
        ("number.raw", "0", {"min": 0, "max": 200, "step": 1}, "number", "set_value", "value", 60),
    ],
)
async def test_configured_toggle_turns_on_at_selected_percentage(
    entity, state, attributes, domain, service, field, value
):
    ramp, call = controller(entity, state, attributes)
    await ramp.action(entity, "configured", 30)
    call.assert_awaited_once_with(
        domain, service, {"entity_id": entity, field: value}, blocking=True
    )


async def test_hue_actual_level_is_used_instead_of_ha_transition_target():
    ramp, call = controller("light.test", "on", {"brightness": 255})
    await ramp.action("light.test", "previous", 100, actual_level=54.15)
    assert ramp.previous["light.test"] == 54.15
    call.assert_awaited_once_with("light", "turn_off", {"entity_id": "light.test"}, blocking=True)


async def test_number_dial_rotates_in_both_directions_without_endpoint_reversal():
    ramp, call = controller("number.pwm", "59", {"min": 0, "max": 100, "step": 1})
    key = ("dial", 0)
    ramp.rotate(key, ("number.pwm",), 10, 0.02)
    await ramp.ramps[key].task
    assert call.await_args.args[2]["value"] == 69
    ramp.rotate(key, ("number.pwm",), -20, 0.02)
    await ramp.ramps[key].task
    assert call.await_args.args[2]["value"] == 49
    await ramp.close()


@pytest.mark.parametrize(
    "entity,state,attributes",
    [
        ("number.pwm", "35", {"min": 0, "max": 100, "step": 1}),
        ("fan.test", "on", {"percentage": 35}),
    ],
)
async def test_one_way_percentage_actions_do_not_toggle(entity, state, attributes):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from custom_components.hue_reconfigo.percentage import PercentageRamp

    current = SimpleNamespace(state=state, attributes=attributes)
    call = AsyncMock()
    ramp = PercentageRamp(
        SimpleNamespace(
            states=SimpleNamespace(get=lambda _: current), services=SimpleNamespace(async_call=call)
        ),
        lambda coro: None,
    )
    await ramp.action(entity, "on", 70)
    assert call.await_args.args[2].get("value", call.await_args.args[2].get("percentage")) == 70
    await ramp.action(entity, "off", 70)
    assert call.await_args.args[2].get("value", call.await_args.args[2].get("percentage")) == 0
