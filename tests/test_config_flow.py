import asyncio
from types import MappingProxyType, SimpleNamespace

import pytest
from homeassistant.config_entries import (
    ConfigEntries,
    ConfigEntry,
    ConfigEntryState,
    ConfigSubentry,
)
from homeassistant.core import HomeAssistant

from custom_components.hue_fluid_dimmer.config_flow import (
    HueFluidDimmerFlow,
    HueFluidDimmerOptionsFlow,
    TapDialSubentryFlow,
)
from custom_components.hue_fluid_dimmer.const import CONF_RESOURCE, DOMAIN, SUBENTRY_TAP_DIAL


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


def subentry_flow(tmp_path, bindings):
    flow = TapDialSubentryFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    config_entry = entry()
    flow.hass.config_entries = ConfigEntries(flow.hass, {})
    flow.hass.config_entries._entries[config_entry.entry_id] = config_entry
    for rid, binding in bindings.items():
        sub = ConfigSubentry(
            subentry_type=SUBENTRY_TAP_DIAL,
            unique_id=rid,
            title=rid,
            data=MappingProxyType({CONF_RESOURCE: rid, **binding}),
        )
        flow.hass.config_entries.async_add_subentry(config_entry, sub)
    selected = next(sub for sub in config_entry.subentries.values() if sub.unique_id == "dial-a")
    flow.handler = (config_entry.entry_id, SUBENTRY_TAP_DIAL)
    flow.context = {"source": "reconfigure", "subentry_id": selected.subentry_id}
    return flow, config_entry


async def test_reconfigure_keeps_other_controllers_and_clears_button(tmp_path):
    flow, config_entry = subentry_flow(
        tmp_path,
        {"dial-a": {"button_1": "scene.old"}, "dial-b": {"enabled": False}},
    )
    updates = []

    async def listener(hass, updated_entry):
        updates.append(updated_entry.entry_id)

    config_entry.add_update_listener(listener)
    result = await flow.async_step_reconfigure(
        {"enabled": True, "lights": ["light.test"], "sensitivity": 1.5, "transition": 1}
    )
    bindings = {sub.unique_id: sub.data for sub in config_entry.subentries.values()}
    assert result["type"] == "abort" and result["reason"] == "reconfigure_successful"
    assert bindings["dial-b"]["enabled"] is False
    assert bindings["dial-a"]["enabled"] is True
    assert bindings["dial-a"][CONF_RESOURCE] == "dial-a"
    assert "button_1" not in bindings["dial-a"]
    assert config_entry.supported_subentry_types[SUBENTRY_TAP_DIAL]["supports_reconfigure"]
    await asyncio.sleep(0)
    assert updates == [config_entry.entry_id]
    await flow.hass.async_stop()


async def test_reconfigure_opens_specific_controller_without_device_lookup(tmp_path):
    flow, _ = subentry_flow(tmp_path, {"dial-a": {"enabled": True, "lights": ["light.test"]}})
    result = await flow.async_step_reconfigure()
    assert result["step_id"] == "reconfigure"
    assert result["description_placeholders"] == {"controller": "dial-a"}
    defaults = result["data_schema"]({})
    assert defaults["enabled"] is True and defaults["lights"] == ["light.test"]
    await flow.hass.async_stop()


async def test_enabled_requires_lights(tmp_path):
    flow, _ = subentry_flow(tmp_path, {"dial-a": {}})
    result = await flow.async_step_reconfigure({"enabled": True})
    assert result["errors"] == {"lights": "lights_required"}
    await flow.hass.async_stop()


async def test_add_controller_excludes_existing_rows_and_creates_binding(tmp_path):
    flow, config_entry = subentry_flow(tmp_path, {"dial-a": {}})
    flow.context = {"source": "user"}
    config_entry.runtime_data = SimpleNamespace(
        controllers=lambda: {"dial-a": "Kitchen", "dial-b": "Bedroom"}
    )
    result = await flow.async_step_user()
    with pytest.raises(Exception):
        result["data_schema"]({"controller": "dial-a"})
    result = await flow.async_step_user({"controller": "dial-b"})
    assert result["step_id"] == "binding"
    result = await flow.async_step_binding(
        {"enabled": True, "lights": ["light.bedroom"], "sensitivity": 1.5, "transition": 1}
    )
    assert result["type"] == "create_entry" and result["title"] == "Bedroom"
    assert result["unique_id"] == "dial-b"
    assert result["data"][CONF_RESOURCE] == "dial-b"
    await flow.hass.async_stop()


async def test_all_discovered_controllers_already_listed(tmp_path):
    flow, config_entry = subentry_flow(tmp_path, {"dial-a": {}})
    flow.context = {"source": "user"}
    config_entry.runtime_data = SimpleNamespace(controllers=lambda: {"dial-a": "Kitchen"})
    result = await flow.async_step_user()
    assert result["reason"] == "no_unconfigured_controllers"
    await flow.hass.async_stop()


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
