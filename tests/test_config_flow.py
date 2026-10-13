from types import MappingProxyType, SimpleNamespace

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.hue_fluid_dimmer.config_flow import (
    HueFluidDimmerFlow,
    HueFluidDimmerOptionsFlow,
)
from custom_components.hue_fluid_dimmer.const import CONF_BINDINGS, DOMAIN


def entry(options=None):
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test",
        data={"hue_entry_id": "hue-test"},
        options=options or {},
        source="user",
        unique_id="hue-test",
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )


def options_flow(tmp_path, options=None):
    flow = HueFluidDimmerOptionsFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    config_entry = entry(options)
    flow.handler = config_entry.entry_id
    flow.hass.config_entries = SimpleNamespace(async_get_known_entry=lambda entry_id: config_entry)
    return flow


async def test_polling_form_uses_real_ha_schema(tmp_path):
    flow = options_flow(tmp_path)
    result = await flow.async_step_polling()
    validated = result["data_schema"](
        {"polling_mode": "continuous", "poll_interval": 0.1, "active_window": 3}
    )
    assert validated["poll_interval"] == 0.1
    invalid = {"polling_mode": "continuous", "poll_interval": 0.01, "active_window": 3}
    with pytest.raises(Exception, match="too small"):
        result["data_schema"](invalid)


async def test_binding_keeps_other_controllers_and_clears_button(tmp_path):
    flow = options_flow(
        tmp_path,
        {CONF_BINDINGS: {"dial-a": {"button_1": "scene.old"}, "dial-b": {"enabled": False}}},
    )
    flow.resource_id = "dial-a"
    result = await flow.async_step_binding(
        {"enabled": True, "lights": ["light.test"], "sensitivity": 1.5, "transition": 1}
    )
    assert result["data"][CONF_BINDINGS]["dial-b"] == {"enabled": False}
    assert "button_1" not in result["data"][CONF_BINDINGS]["dial-a"]


async def test_enabled_requires_lights(tmp_path):
    flow = options_flow(tmp_path)
    flow.resource_id = "dial-a"
    result = await flow.async_step_binding({"enabled": True})
    assert result["errors"] == {"lights": "lights_required"}


async def test_setup_requires_official_hue_v2(tmp_path):
    flow = HueFluidDimmerFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    flow.hass.config_entries = SimpleNamespace(
        async_entries=lambda domain: [
            SimpleNamespace(data={"api_version": 1}, state=ConfigEntryState.LOADED)
        ]
    )
    result = await flow.async_step_user()
    assert result["reason"] == "no_hue"
