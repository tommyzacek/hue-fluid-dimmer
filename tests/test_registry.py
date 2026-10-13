"""Upgrade registry entries without disturbing Hue devices or controller bindings."""

from types import MappingProxyType, SimpleNamespace

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.hue_fluid_dimmer import register_controllers
from custom_components.hue_fluid_dimmer.const import DOMAIN


async def test_upgrade_keeps_devices_and_options_but_removes_only_own_events(
    tmp_path, monkeypatch, resource
):
    hass = HomeAssistant(str(tmp_path))
    options = {"controllers": {"dial-a": {"enabled": True, "lights": ["light.test"]}}}
    entries = {}
    for domain in (DOMAIN, "hue"):
        entries[domain] = ConfigEntry(
            version=1,
            minor_version=1,
            domain=domain,
            title=domain,
            data={},
            options=options if domain == DOMAIN else {},
            source="user",
            unique_id=domain,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )
    by_id = {entry.entry_id: entry for entry in entries.values()}
    hass.config_entries = SimpleNamespace(async_get_entry=by_id.get)
    devices = dr.DeviceRegistry(hass)
    entities = er.EntityRegistry(hass)
    monkeypatch.setattr(dr, "async_get", lambda h: devices)
    monkeypatch.setattr(er, "async_get", lambda h: entities)
    await devices.async_load()
    await entities.async_load()
    entry = entries[DOMAIN]
    entry.runtime_data = SimpleNamespace(
        resources=[resource(), resource(resource_id="dial-b", owner_id="owner-b")],
        controllers=lambda: {"dial-a": "Kitchen", "dial-b": "Bedroom"},
    )
    original = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "owner-a")}, name="Kitchen"
    )
    devices.async_update_device(original.id, name_by_user="My dial")
    obsolete = entities.async_get_or_create(
        "event", DOMAIN, "dial-a", config_entry=entry, device_id=original.id
    )
    hue = devices.async_get_or_create(
        config_entry_id=entries["hue"].entry_id,
        identifiers={("hue", "owner-a")},
        name="Kitchen",
    )
    battery = entities.async_get_or_create(
        "sensor", "hue", "battery-a", config_entry=entries["hue"], device_id=hue.id
    )

    register_controllers(hass, entry)
    register_controllers(hass, entry)  # Reload must not duplicate the device list.

    assert entities.async_get(obsolete.entity_id) is None
    assert entities.async_get(battery.entity_id) is battery
    assert devices.async_get(hue.id) is hue
    kept = devices.async_get(original.id)
    assert kept.name_by_user == "My dial"
    assert kept.configuration_url.endswith(f"#config_entry={entry.entry_id}")
    assert len(dr.async_entries_for_config_entry(devices, entry.entry_id)) == 2
    assert not er.async_entries_for_config_entry(entities, entry.entry_id)
    assert entry.options == options
    await hass.async_stop()
