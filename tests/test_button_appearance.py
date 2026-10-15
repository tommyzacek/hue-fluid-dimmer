"""Shared button appearance, legacy migration and Motion recovery integration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from test_runtime import make_runtime

from custom_components.hue_fluid_dimmer.bindings import form_values, parse_form
from custom_components.hue_fluid_dimmer.config_flow import binding_schema
from custom_components.hue_fluid_dimmer.motion import START_DEFAULTS


@pytest.mark.parametrize("kind", ["tap_dial", "dimmer", "button"])
@pytest.mark.parametrize("action", ["short", "long", "double", "triple"])
def test_each_controller_gesture_preserves_independent_brightness_and_color(kind, action):
    values = form_values({"controller_kind": kind})
    values["shared_targets"] = ["light.a"]
    values["button_1"].update(
        {
            f"{action}_enabled": True,
            f"{action}_targets": ["light.a"],
            f"{action}_operation": {
                "operation": "toggle",
                "percentage": 100,
                "startup": {
                    **START_DEFAULTS,
                    "brightness": "configured",
                    "percentage": 42,
                    "color": "temperature",
                    "temperature": 3150,
                },
            },
        }
    )
    binding, error = parse_form(values)
    assert error is None
    startup = binding["button_1"][f"{action}_startup"]
    assert startup["percentage"] == 42
    assert startup["temperature"] == 3200
    assert form_values(binding)["button_1"][f"{action}_startup"] == startup


def test_legacy_configured_level_populates_new_editor_without_reset():
    schema = binding_schema(
        {
            "button_1": {
                "short": ["light.a"],
                "short_operation": "configured",
                "short_percentage": 37,
            }
        }
    )
    value = schema({})["button_1"]["short_operation"]
    assert value["startup"]["brightness"] == "configured"
    assert value["startup"]["percentage"] == 37


def test_invalid_color_rejected_and_disabled_action_does_not_retain_appearance():
    values = form_values({"button_1": ["light.a"]})
    values["button_1"]["short_operation"] = {
        "operation": "toggle",
        "startup": {"color": "rgb", "rgb": [-1, 0, 0]},
    }
    assert parse_form(values)[1] == "motion_start_invalid"
    values["button_1"]["short_enabled"] = False
    binding, error = parse_form(values)
    assert error is None
    assert "button_1" not in binding


async def setup_runtime(monkeypatch, states):
    runtime, _ = make_runtime(monkeypatch, {})
    call = AsyncMock()
    runtime.hass.states = SimpleNamespace(get=states.get)
    runtime.hass.services = SimpleNamespace(async_call=call)
    runtime.adaptive.mark = AsyncMock()
    runtime.hue_dimming_resources = lambda selected: []
    return runtime, call


async def test_previous_button_restores_motion_pre_fade_level_and_sends_no_color(monkeypatch):
    runtime, call = await setup_runtime(
        monkeypatch, {"light.a": SimpleNamespace(state="off", attributes={"brightness": 30})}
    )
    runtime.motion.remembered["light.a"] = {"brightness": 204, "owner": "motion-a"}
    binding = {"button_1": {"short": ["light.a"], "short_startup": dict(START_DEFAULTS)}}
    await runtime.button("dimmer", binding, 1)
    data = call.await_args.args[2]
    assert data["brightness"] == 204
    assert data["transition"] == 0.5
    assert not {"rgb_color", "color_temp_kelvin"} & data.keys()
    runtime.adaptive.mark.assert_not_awaited()
    await runtime.close()


async def test_button_configured_color_marks_only_color_and_clamps_supported_temperature(
    monkeypatch,
):
    state = SimpleNamespace(
        state="off",
        attributes={
            "supported_color_modes": ["color_temp"],
            "min_color_temp_kelvin": 2200,
            "max_color_temp_kelvin": 6500,
        },
    )
    runtime, call = await setup_runtime(monkeypatch, {"light.a": state})
    binding = {
        "button_1": {
            "short": ["light.a"],
            "short_startup": {**START_DEFAULTS, "color": "temperature", "temperature": 1800},
        }
    }
    await runtime.button("dial", binding, 1)
    data = call.await_args.args[2]
    assert data["color_temp_kelvin"] == 2200
    assert "brightness" not in data and "brightness_pct" not in data
    runtime.adaptive.mark.assert_awaited_once_with(["light.a"], component="color")
    await runtime.close()


async def test_button_off_captures_actual_level_and_next_on_restores_it(monkeypatch):
    state = SimpleNamespace(state="on", attributes={"brightness": 153})
    runtime, call = await setup_runtime(monkeypatch, {"light.a": state})
    binding = {"button_1": {"short": ["light.a"], "short_startup": dict(START_DEFAULTS)}}
    await runtime.button("button", binding, 1)
    assert call.await_args.args[:2] == ("light", "turn_off")
    assert runtime.motion.remembered["light.a"]["brightness"] == 153
    state.state = "off"
    await runtime.button("button", binding, 1)
    assert call.await_args.args[2]["brightness"] == 153
    await runtime.close()


async def test_unsupported_rgb_is_not_sent_and_groups_restore_per_member(monkeypatch):
    states = {
        "light.group": SimpleNamespace(
            state="off", attributes={"entity_id": ["light.a", "light.b"]}
        ),
        "light.a": SimpleNamespace(
            state="off", attributes={"supported_color_modes": ["brightness"]}
        ),
        "light.b": SimpleNamespace(state="off", attributes={"supported_color_modes": ["rgb"]}),
    }
    runtime, call = await setup_runtime(monkeypatch, states)
    runtime.motion.remembered.update(
        {"light.a": {"brightness": 100}, "light.b": {"brightness": 200}}
    )
    await runtime.button(
        "button",
        {
            "button_1": {
                "short": ["light.group"],
                "short_startup": {**START_DEFAULTS, "color": "rgb", "rgb": [20, 30, 40]},
            }
        },
        1,
    )
    calls = {c.args[2]["entity_id"][0]: c.args[2] for c in call.await_args_list}
    assert calls["light.a"]["brightness"] == 100
    assert "rgb_color" not in calls["light.a"]
    assert calls["light.b"]["brightness"] == 200
    assert calls["light.b"]["rgb_color"] == [20, 30, 40]
    await runtime.close()


@pytest.mark.parametrize("kind", ["tap_dial", "dimmer", "button"])
@pytest.mark.parametrize("action", ["short", "long", "double", "triple"])
@pytest.mark.parametrize("operation", ["on", "off"])
def test_one_way_power_roundtrips_for_every_button_gesture(kind, action, operation):
    values = form_values({"controller_kind": kind})
    values["shared_targets"] = ["light.a"]
    values["button_1"].update(
        {
            f"{action}_enabled": True,
            f"{action}_targets": ["light.a"],
            f"{action}_operation": {
                "operation": operation,
                "startup": {**START_DEFAULTS, "color": "rgb", "rgb": [255, 0, 0]},
            },
        }
    )
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_1"][f"{action}_operation"] == operation
    assert (f"{action}_startup" in binding["button_1"]) is (operation == "on")
    assert form_values(binding)["button_1"][f"{action}_operation"] == operation


@pytest.mark.parametrize("state", ["on", "off"])
async def test_on_only_changes_color_without_ever_switching_off(monkeypatch, state):
    runtime, call = await setup_runtime(
        monkeypatch,
        {
            "light.a": SimpleNamespace(
                state=state, attributes={"supported_color_modes": ["rgb"], "brightness": 128}
            )
        },
    )
    binding = {
        "button_1": {
            "double": ["light.a"],
            "double_operation": "on",
            "double_startup": {**START_DEFAULTS, "color": "rgb", "rgb": [255, 0, 0]},
        }
    }
    await runtime.button("dimmer", binding, 1, "double")
    assert call.await_count == 1
    assert call.await_args.args[1] == "turn_on"
    assert call.await_args.args[2]["rgb_color"] == [255, 0, 0]
    assert "brightness" not in call.await_args.args[2]
    runtime.adaptive.mark.assert_awaited_once_with(["light.a"], component="color")
    await runtime.close()


@pytest.mark.parametrize("state", ["on", "off"])
async def test_off_only_never_switches_on_or_sends_color(monkeypatch, state):
    runtime, call = await setup_runtime(
        monkeypatch,
        {
            "light.a": SimpleNamespace(
                state=state, attributes={"supported_color_modes": ["rgb"], "brightness": 128}
            )
        },
    )
    await runtime.button(
        "button", {"button_1": {"short": ["light.a"], "short_operation": "off"}}, 1
    )
    call.assert_awaited_once_with("light", "turn_off", {"entity_id": ["light.a"]}, blocking=True)
    runtime.adaptive.mark.assert_not_awaited()
    await runtime.close()
