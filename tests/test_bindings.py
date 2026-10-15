import probatio as p
import pytest
from homeassistant.helpers import config_validation as cv

from custom_components.hue_reconfigo.bindings import form_values, parse_form, resolve_binding
from custom_components.hue_reconfigo.config_flow import VisibleOperation, binding_schema


@pytest.mark.parametrize("selection", ["light.bulb", "light.group", ["light.a", "light.b"]])
def test_shared_selection_is_live_and_preserves_groups(selection):
    raw = {"dial_source": "button_1", "button_1": selection}
    assert resolve_binding(raw)["lights"] == (
        [selection] if isinstance(selection, str) else selection
    )
    raw["button_1"] = ["light.changed_group"]
    assert resolve_binding(raw)["lights"] == ["light.changed_group"]


@pytest.mark.parametrize("target", ["scene.evening", "script.dynamic"])
def test_shared_scene_and_script_are_rejected_without_guessing_lights(target):
    values = form_values({"enabled": True, "dial_source": "button_1", "button_1": target})
    _, error = parse_form(values)
    assert error == (
        "button_targets_invalid" if target.startswith("scene.") else "dial_target_required"
    )
    values["button_2"] = values["button_1"]
    values["button_1"] = form_values({"button_1": ["light.group"]})["button_1"]
    binding, error = parse_form(values)
    if target.startswith("scene."):
        assert error == "button_targets_invalid"
    else:
        assert error is None and binding["button_2"] == {"short": [target]}


def test_long_dimming_requires_lights_and_defaults_to_up():
    values = form_values({"button_1": {"long": ["light.group"]}})
    values["button_1"].update(long_operation="dimming", long_direction="down")
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_1"] == {
        "long": ["light.group"],
        "long_mode": "dimming",
    }
    values["button_1"]["long_targets"] = ["scene.evening"]
    _, error = parse_form(values)
    assert error == "button_targets_invalid"


@pytest.mark.parametrize("target", ["fan.test", "number.pwm"])
def test_button_only_percentage_control_does_not_require_dial_lights(target):
    values = form_values({"enabled": True, "button_1": {"long": [target], "long_mode": "dimming"}})
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_1"]["long"] == [target]


@pytest.mark.parametrize("action", ["short", "long", "double", "triple"])
@pytest.mark.parametrize("operation", ["toggle", "previous", "configured"])
def test_all_press_types_accept_number_actions_and_preserve_operation(action, operation):
    raw = {
        "button_1": {
            action: ["number.pwm"],
            f"{action}_operation": operation,
            f"{action}_percentage": 35,
        }
    }
    values = form_values(raw)
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_1"][action] == ["number.pwm"]
    assert binding["button_1"][f"{action}_operation"] == operation
    assert binding["button_1"][f"{action}_percentage"] == 35
    values["button_1"][f"{action}_enabled"] = False
    binding, error = parse_form(values)
    assert error is None
    assert "button_1" not in binding


def test_smooth_adjustment_only_appears_in_long_press_operation_list():
    assert (
        "dimming"
        in VisibleOperation("long").serialize()["selector"]["hrc_button_action"]["options"]
    )
    for action in ("short", "double", "triple"):
        assert (
            "dimming"
            not in VisibleOperation(action).serialize()["selector"]["hrc_button_action"]["options"]
        )


def test_existing_long_dimming_binding_keeps_its_mode_in_the_unified_form():
    values = form_values({"button_1": {"long": ["number.pwm"], "long_mode": "dimming"}})
    assert values["button_1"]["long_operation"] == "dimming"
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_1"] == {"long": ["number.pwm"], "long_mode": "dimming"}
    values["button_1"]["long_operation"] = "previous"
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_1"]["long_mode"] == "action"


def test_profile_switch_preserves_custom_values_and_legacy_settings():
    old = {"enabled": True, "lights": ["light.group"], "sensitivity": 2.2, "transition": 0.8}
    values = form_values(old)
    assert values["dial"]["profile"] == "custom"
    values["dial"]["profile"] = "gentle"
    binding, error = parse_form(values)
    assert error is None
    assert binding["sensitivity"] == 1.2 and binding["transition"] == 1.0
    restored = form_values(binding)
    restored["dial"]["profile"] = "custom"
    binding, _ = parse_form(restored)
    assert binding["sensitivity"] == 2.2 and binding["transition"] == 0.8


def test_ui_serialization_contains_conditional_fields_and_collapsed_buttons():
    fields = p.to_field_list(binding_schema({}), custom_serializer=cv.custom_serializer)
    dial = next(f for f in fields if f["name"] == "dial")
    children = {f["name"]: f for f in dial["schema"]}
    assert "lights" not in children and "source" not in children
    assert children["sensitivity"]["visible"] == {"field": "profile", "value": "custom"}
    assert children["transition"]["visible"] == children["sensitivity"]["visible"]
    assert all(not f["expanded"] for f in fields if f["name"].startswith("button_"))
    button_1 = next(f for f in fields if f["name"] == "button_1")
    assert "long_direction" not in {f["name"] for f in button_1["schema"]}


def test_buttons_reject_mixed_targets_and_preserve_empty_optional_fields():
    values = form_values({"button_1": ["light.a", "scene.b"]})
    assert parse_form(values)[1] == "button_targets_invalid"
    values["button_1"]["short_enabled"] = False
    binding, error = parse_form(values)
    assert error is None and "button_1" not in binding


def test_disabled_gestures_remove_hidden_targets_and_shared_dial_uses_short():
    values = form_values(
        {
            "enabled": True,
            "dial_source": "button_2",
            "button_2": {"short": ["light.group"], "double": ["scene.evening"]},
        }
    )
    values["button_2"]["double_enabled"] = False
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_2"] == {"short": ["light.group"]}
    assert resolve_binding(binding)["lights"] == ["light.group"]
    values["button_2"]["short_enabled"] = False
    binding, error = parse_form(values)
    assert error is None and "button_2" not in binding
    assert resolve_binding(binding)["lights"] == ["light.group"]


def test_dial_takeover_uses_own_target_without_short_press():
    values = form_values(
        {"enabled": True, "button_1": ["light.main"], "button_2": {"short": ["number.pwm"]}}
    )
    values["button_2"].update(long_enabled=True, long_operation="dial", long_targets=["fan.other"])
    binding, error = parse_form(values)
    assert error is None
    assert binding["button_2"]["long"] == ["fan.other"]
    assert binding["button_2"]["long_operation"] == "dial"
    values["button_2"]["short_enabled"] = False
    assert parse_form(values)[1] is None
    assert (
        "dial"
        not in VisibleOperation("long", 1).serialize()["selector"]["hrc_button_action"]["options"]
    )


def test_enabled_action_requires_target_and_ui_hides_only_its_field():
    values = form_values({})
    values["button_1"]["double_enabled"] = True
    assert parse_form(values)[1] == "button_target_required"
    fields = p.to_field_list(binding_schema({}), custom_serializer=cv.custom_serializer)
    button = next(f for f in fields if f["name"] == "button_1")
    children = {f["name"]: f for f in button["schema"]}
    assert children["double_targets"]["visible"] == {"field": "double_enabled", "value": True}


def test_nonlight_custom_ramp_is_independent_and_preserved():
    values = form_values({"button_1": ["light.main"]})
    values["dial"].update(profile="custom", transition=1.2, nonlight_transition=0.35)
    binding, error = parse_form(values)
    assert error is None
    assert binding["transition"] == 1.2
    assert binding["nonlight_transition"] == 0.35
    values["dial"]["profile"] = "balanced"
    preset, error = parse_form(values)
    assert error is None
    assert preset["transition"] == 1.0
    assert preset["nonlight_transition"] == 0.75
    assert form_values(preset)["dial"]["nonlight_transition"] == 0.35


def test_custom_nonlight_sensitivity_is_independent():
    values = form_values({"button_1": ["light.main"]})
    values["dial"].update(profile="custom", sensitivity=2.3, nonlight_sensitivity=1.25)
    binding, error = parse_form(values)
    assert error is None
    assert binding["sensitivity"] == 2.3
    assert binding["nonlight_sensitivity"] == 1.25
    assert form_values(binding)["dial"]["nonlight_sensitivity"] == 1.25


@pytest.mark.parametrize(
    "profile,light,other", [("gentle", 1.2, 0.75), ("balanced", 2.4, 1.5), ("swift", 4.8, 3)]
)
def test_internal_presets_derive_from_tested_custom_and_enable_adaptive(profile, light, other):
    values = form_values({"button_1": ["light.main"]})
    values["dial"].update(profile=profile, adaptive_transition=False)
    binding, error = parse_form(values)
    assert error is None
    assert binding["sensitivity"] == light
    assert binding["nonlight_sensitivity"] == other
    assert binding["adaptive_transition"] is True
    binding.update(sensitivity=99, nonlight_sensitivity=99, adaptive_transition=False)
    effective = resolve_binding(binding)
    assert effective["sensitivity"] == light
    assert effective["nonlight_sensitivity"] == other
    assert effective["adaptive_transition"] is True
