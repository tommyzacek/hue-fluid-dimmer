"""Temporary Dial routing belongs to the selected gesture, not the short press."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from test_runtime import make_runtime

from custom_components.hue_reconfigo.bindings import button_actions, form_values, parse_form
from custom_components.hue_reconfigo.config_flow import VisibleOperation


@pytest.mark.parametrize("action", ["short", "long", "double", "triple"])
@pytest.mark.parametrize("index", [2, 3, 4])
def test_takeover_has_independent_targets_for_each_gesture(action, index):
    values = form_values({"enabled": True, "button_1": ["light.main"]})
    values[f"button_{index}"].update(
        {
            f"{action}_enabled": True,
            f"{action}_targets": ["number.pwm"],
            f"{action}_operation": "dial",
        }
    )
    binding, error = parse_form(values)
    assert error is None
    assert button_actions(binding, index) == {action: ["number.pwm"]}
    assert binding[f"button_{index}"][f"{action}_operation"] == "dial"
    assert "dial" in VisibleOperation(action, index).options
    if action != "short":
        assert "short" not in button_actions(binding, index)
    restored = form_values(binding)
    restored[f"button_{index}"][f"{action}_enabled"] = False
    assert f"button_{index}" not in parse_form(restored)[0]


@pytest.mark.parametrize("targets", [[], ["script.x"], ["scene.x"], ["light.a", "fan.x"]])
def test_takeover_rejects_non_percentage_or_mixed_targets(targets):
    values = form_values({"button_1": ["light.main"]})
    values["button_2"].update(double_enabled=True, double_targets=targets, double_operation="dial")
    assert parse_form(values)[1] == "dial_target_required"


@pytest.mark.parametrize("kind,index", [("tap_dial", 1), ("button", 1), ("dimmer", 2)])
def test_takeover_is_not_offered_on_unsupported_controllers(kind, index):
    assert "dial" not in VisibleOperation("double", index, kind).options
    values = form_values(
        {"controller_kind": kind, "button_1": ["light.main"], "shared_targets": ["light.main"]}
    )
    values[f"button_{index}"].update(
        double_enabled=True, double_targets=["number.pwm"], double_operation="dial"
    )
    assert parse_form(values)[1] == "dial_target_required"


def test_legacy_explicit_long_target_is_preserved_and_missing_one_falls_back():
    assert button_actions(
        {"button_2": {"short": ["light.a"], "long": ["fan.b"], "long_operation": "dial"}}, 2
    )["long"] == ["fan.b"]
    assert button_actions({"button_2": {"short": ["light.a"], "long_operation": "dial"}}, 2)[
        "long"
    ] == ["light.a"]


@pytest.mark.parametrize("action", ["short", "long", "double", "triple"])
async def test_runtime_takeover_routes_own_target_without_power_action(monkeypatch, action):
    runtime, _ = make_runtime(monkeypatch, {})
    clock = [0.0]
    runtime.dial_routing.clock = lambda: clock[0]
    runtime.hass.services = SimpleNamespace(async_call=AsyncMock())
    runtime.dimmer.rotate = Mock()
    runtime.percentage.rotate = Mock()
    binding = {
        "enabled": True,
        "controller_kind": "tap_dial",
        "lights": ["light.main"],
        "button_2": {action: ["number.pwm"], f"{action}_operation": "dial"},
    }
    if action != "short":
        binding["button_2"]["short"] = ["light.different"]
    await runtime.button("dial", binding, 2, action)
    runtime.hass.services.async_call.assert_not_awaited()
    assert runtime.dial_routing.leases["dial"].targets == ("number.pwm",)
    clock[0] = 4.9
    runtime.rotate_dial("dial", binding, 15)
    assert runtime.percentage.rotate.call_args.args[1] == ("number.pwm",)
    clock[0] = 9.9
    runtime.rotate_dial("dial", binding, 15)
    assert runtime.dimmer.rotate.call_args.args[0]["lights"] == ["light.main"]
    await runtime.close()
