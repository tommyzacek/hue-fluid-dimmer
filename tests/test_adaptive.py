from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.hue_fluid_dimmer.adaptive import AdaptiveCooperation, matches
from custom_components.hue_fluid_dimmer.bindings import form_values, parse_form, resolve_binding


def fake_hass():
    states = {
        "light.room": SimpleNamespace(attributes={"entity_id": ["light.a", "light.b"]}),
        "light.other": SimpleNamespace(attributes={"entity_id": ["light.b", "light.c"]}),
    }
    return SimpleNamespace(states=SimpleNamespace(get=states.get))


def test_matches_overlapping_profiles_without_marking_unmanaged_lights():
    profiles = [
        ("switch.one", {"lights": ["light.a"]}),
        ("switch.two", {"lights": ["light.other"]}),
    ]
    found, partial = matches(fake_hass(), ["light.room"], profiles)
    assert found == [("switch.one", ["light.a"]), ("switch.two", ["light.b"])]
    assert not partial


def test_group_tracked_as_whole_requires_full_coverage():
    profiles = [("switch.one", {"lights": ["light.room"], "expand_light_groups": False})]
    assert matches(fake_hass(), ["light.a"], profiles) == ([], [("switch.one", "light.room")])
    assert matches(fake_hass(), ["light.a", "light.b"], profiles) == (
        [("switch.one", ["light.room"])],
        [],
    )
    assert matches(fake_hass(), ["light.room"], profiles) == ([("switch.one", ["light.room"])], [])


async def test_opt_out_does_not_access_adaptive_lighting():
    hass = SimpleNamespace(services=SimpleNamespace(async_call=AsyncMock()))
    await AdaptiveCooperation(hass, lambda: False).mark(["light.a"])
    hass.services.async_call.assert_not_called()


@pytest.mark.parametrize("enabled", [True, False])
def test_separate_main_dial_targets_and_clearing_override(enabled):
    values = form_values({"enabled": True, "button_1": {"short": ["light.small"]}})
    values["dial"].update(override=enabled, targets=["light.room"])
    binding, error = parse_form(values)
    assert error is None
    assert resolve_binding(binding)["lights"] == (["light.room"] if enabled else ["light.small"])
    if not enabled:
        assert binding["dial_targets"] == []


async def test_marks_all_matching_profiles_through_public_service(monkeypatch):
    from custom_components.hue_fluid_dimmer import adaptive

    hass = fake_hass()
    hass.services = SimpleNamespace(has_service=lambda *args: True, async_call=AsyncMock())
    entries = {}
    for switch, lights in [("switch.one", ["light.a"]), ("switch.two", ["light.b"])]:
        entries[switch] = SimpleNamespace(data={}, options={"lights": lights})
    states = {
        "switch.one": SimpleNamespace(state="on", attributes={"configuration": {}}),
        "switch.two": SimpleNamespace(state="on", attributes={"configuration": {}}),
    }
    original_get = hass.states.get
    hass.states.get = lambda entity: states.get(entity) or original_get(entity)
    hass.config_entries = SimpleNamespace(async_get_entry=entries.get)
    registry = SimpleNamespace(
        entities={
            key: SimpleNamespace(platform="adaptive_lighting", entity_id=key, config_entry_id=key)
            for key in entries
        }
    )
    monkeypatch.setattr(adaptive.er, "async_get", lambda hass: registry)
    await AdaptiveCooperation(hass, lambda: True).mark(["light.room"])
    assert hass.services.async_call.await_count == 2
    for switch, light in [("switch.one", "light.a"), ("switch.two", "light.b")]:
        hass.services.async_call.assert_any_await(
            "adaptive_lighting",
            "set_manual_control",
            {"entity_id": switch, "lights": [light], "manual_control": "brightness"},
            blocking=True,
        )


@pytest.mark.parametrize(
    "component,prior,expected",
    [
        ("color", {}, "color"),
        ("both", {}, True),
        ("color", {"manual_control_brightness": ["light.a"]}, True),
        ("brightness", {"manual_control_color": ["light.a"]}, True),
    ],
)
async def test_explicit_color_and_brightness_preserve_each_other(
    monkeypatch, component, prior, expected
):
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity: SimpleNamespace(attributes=prior)),
        services=SimpleNamespace(has_service=lambda *args: True, async_call=AsyncMock()),
    )
    helper = AdaptiveCooperation(hass, lambda: True)
    monkeypatch.setattr(helper, "profiles", lambda: [("switch.al", {"lights": ["light.a"]})])
    await helper.mark(["light.a"], component=component)
    assert hass.services.async_call.await_args.args[2]["manual_control"] == expected
