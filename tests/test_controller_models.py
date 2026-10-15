"""Button/Dimmer forms, routing, cycle actions and held-direction rules."""

import asyncio
from unittest.mock import AsyncMock

import probatio as p
import pytest
from homeassistant.helpers import config_validation as cv
from test_runtime import make_runtime

from custom_components.hue_fluid_dimmer.bindings import button_actions, form_values, parse_form
from custom_components.hue_fluid_dimmer.config_flow import binding_schema
from custom_components.hue_fluid_dimmer.controller_models import HoldDirections, controller_kind


@pytest.mark.parametrize(
    "model,kind",
    [
        ("ROM001", "button"),
        ("RDM003", "button"),
        ("RDM005", "button"),
        ("RWL022", "dimmer"),
        ("RWL021", None),
        ("COM001", None),
    ],
)
def test_supported_models_are_explicit(model, kind):
    assert controller_kind(model) == kind


def test_thresholds_apply_at_start_and_middle_alternates_per_button():
    directions = HoldDirections()
    key = ("kitchen", 1)
    assert directions.choose(key, 29.99) == "up"
    assert directions.choose(key, 50) == "down"
    assert directions.choose(key, 50) == "up"
    assert directions.choose(("other", 1), 50) == "up"
    assert directions.choose(key, 60.01) == "down"
    assert directions.choose(key, 0) == "up"
    assert directions.choose(key, 100) == "down"
    assert directions.choose(key, 0, "down") == "down"


@pytest.mark.parametrize("kind,count", [("button", 1), ("dimmer", 4)])
def test_nonrotary_forms_have_no_dial_and_use_shared_targets(kind, count):
    schema = binding_schema({"controller_kind": kind})
    serialized = p.to_field_list(schema, custom_serializer=cv.custom_serializer)
    names = [x["name"] for x in serialized]
    assert "dial" not in names
    assert "shared_targets" in names
    assert sum(x.startswith("button_") for x in names) == count
    values = form_values({"controller_kind": kind})
    values["enabled"] = True
    values["shared_targets"] = ["light.bath"]
    # The actual schema excludes the internal kind; flow injects it server-side.
    submitted = {k: v for k, v in values.items() if k in names}
    validated = schema(submitted)
    binding, error = parse_form({**validated, "controller_kind": kind})
    assert error is None
    assert binding["button_1"]["short"] == ["light.bath"]
    if kind == "dimmer":
        assert binding["button_2"]["long_direction"] == "up"
        assert binding["button_3"]["long_direction"] == "down"


async def test_discovery_keeps_rotary_ids_and_maps_buttons_by_owner(monkeypatch, resource):
    runtime, _ = make_runtime(monkeypatch, {})
    runtime.client.rotary_resources = AsyncMock(return_value=[resource()])
    runtime.client.device_resources = AsyncMock(
        return_value=[
            {"id": "smart", "metadata": {"name": "Button"}, "product_data": {"model_id": "RDM005"}},
            {
                "id": "dimmer",
                "metadata": {"name": "Dimmer"},
                "product_data": {"model_id": "RWL022"},
            },
            {"id": "unsupported", "product_data": {"model_id": "ROM002"}},
        ]
    )
    await runtime.initialize()
    assert runtime.controllers()["smart"] == "Button"
    assert "dial-a" in runtime.controllers() and "unsupported" not in runtime.controllers()
    runtime.map_buttons(
        [
            {"id": "smart-key", "owner": {"rid": "smart"}, "metadata": {"control_id": 1}},
            {"id": "dim-key", "owner": {"rid": "dimmer"}, "metadata": {"control_id": 3}},
        ]
    )
    assert runtime.button_map == {"smart-key": ("smart", 1), "dim-key": ("dimmer", 3)}
    await runtime.close()


async def test_release_before_native_initial_read_prevents_late_dimming(monkeypatch):
    binding = {"enabled": True, "button_1": {"long": ["light.test"], "long_mode": "dimming"}}
    runtime, _ = make_runtime(monkeypatch, {"controllers": {"remote": binding}})
    runtime.hue_dimming_resources = lambda selected: (("light", "native"),)
    wait = asyncio.Event()

    async def read(*args):
        await wait.wait()
        return 50

    runtime.client.read_brightness = read
    runtime.client.brightness_delta = AsyncMock()
    runtime.client.stop_dimming = AsyncMock()
    runtime.button_hold_event("remote", 1, "start", 1)
    await asyncio.sleep(0)
    runtime.button_hold_event("remote", 1, "release", 1.1)
    wait.set()
    await asyncio.gather(*tuple(runtime.action_tasks), return_exceptions=True)
    runtime.client.brightness_delta.assert_not_awaited()
    runtime.client.stop_dimming.assert_awaited_once_with("light", "native")
    await runtime.close()


def test_explicit_target_override_can_be_removed_without_stale_target():
    values = form_values({"controller_kind": "button"})
    values["shared_targets"] = ["light.default"]
    values["button_1"]["long_enabled"] = False
    values["button_1"]["short_other_targets"] = True
    values["button_1"]["short_targets"] = ["light.other"]
    binding, error = parse_form(values)
    assert error is None
    assert button_actions(binding, 1)["short"] == ["light.other"]
    values = form_values(binding)
    values["button_1"]["short_other_targets"] = False
    binding, error = parse_form(values)
    assert error is None
    assert button_actions(binding, 1)["short"] == ["light.default"]
    values = form_values(binding)
    values["shared_targets"] = ["light.changed"]
    binding, error = parse_form(values)
    assert error is None
    assert button_actions(binding, 1)["short"] == ["light.changed"]


def test_scene_controls_are_removed_from_form_and_parser():
    fields = p.to_field_list(
        binding_schema({"controller_kind": "button"}), custom_serializer=cv.custom_serializer
    )
    button = next(field for field in fields if field["name"] == "button_1")
    children = {field["name"]: field for field in button["schema"]}
    assert "scenes" not in children and "cycle_off" not in children
    assert "cycle" not in children["short_operation"]["selector"]["select"]["options"]
    assert "scene" not in children["short_targets"]["selector"]["entity"]["domain"]
    values = form_values({"controller_kind": "button"})
    values["button_1"].update(
        short_other_targets=True, short_targets=["scene.a"], long_enabled=False
    )
    assert parse_form(values)[1] == "button_targets_invalid"


@pytest.mark.parametrize(
    "entity,unique,expected",
    [
        ("sensor.bath_lux", "light-resource", "lux"),
        ("switch.bath_light_enabled", "light-resource", "lux_enabled"),
        ("binary_sensor.bath_motion", "motion-resource", "motion"),
        ("switch.bath_motion_enabled", "motion-resource", "motion_enabled"),
    ],
)
def test_motion_mapping_separates_readings_from_enable_switches(entity, unique, expected):
    from custom_components.hue_fluid_dimmer.controller_models import motion_service_role

    assert (
        motion_service_role(
            entity, unique, {"motion": "motion-resource", "light_level": "light-resource"}
        )
        == expected
    )
