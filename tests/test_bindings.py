import probatio as p
import pytest
from homeassistant.helpers import config_validation as cv

from custom_components.hue_fluid_dimmer.bindings import form_values, parse_form, resolve_binding
from custom_components.hue_fluid_dimmer.config_flow import binding_schema


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
    assert error == "button_lights_only"
    values["dial"]["source"] = "custom"
    values["dial"]["lights"] = ["light.group"]
    binding, error = parse_form(values)
    assert error is None and binding["button_1"] == [target]


def test_profile_switch_preserves_custom_values_and_legacy_settings():
    old = {"enabled": True, "lights": ["light.group"], "sensitivity": 2.2, "transition": 0.8}
    values = form_values(old)
    assert values["dial"]["profile"] == "custom"
    values["dial"]["profile"] = "gentle"
    binding, error = parse_form(values)
    assert error is None
    assert binding["sensitivity"] == 0.75 and binding["transition"] == 1.0
    restored = form_values(binding)
    restored["dial"]["profile"] = "custom"
    binding, _ = parse_form(restored)
    assert binding["sensitivity"] == 2.2 and binding["transition"] == 0.8


def test_ui_serialization_contains_conditional_fields_and_collapsed_buttons():
    fields = p.to_field_list(binding_schema({}), custom_serializer=cv.custom_serializer)
    dial = next(f for f in fields if f["name"] == "dial")
    children = {f["name"]: f for f in dial["schema"]}
    assert children["lights"]["visible"] == {"field": "source", "value": "custom"}
    assert children["sensitivity"]["visible"] == {"field": "profile", "value": "custom"}
    assert children["transition"]["visible"] == children["sensitivity"]["visible"]
    assert all(not f["expanded"] for f in fields if f["name"].startswith("button_"))


def test_buttons_reject_mixed_targets_and_preserve_empty_optional_fields():
    values = form_values({"button_1": ["light.a", "scene.b"]})
    assert parse_form(values)[1] == "button_targets_invalid"
    values["button_1"]["targets"] = []
    binding, error = parse_form(values)
    assert error is None and "button_1" not in binding
