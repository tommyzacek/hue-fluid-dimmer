"""Upgrade registry entries without disturbing Hue devices or controller bindings."""

from types import MappingProxyType, SimpleNamespace

from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.hue_reconfigo.configuration import (
    controller_binding,
    initialize_controllers,
)
from custom_components.hue_reconfigo.const import DOMAIN


async def test_upgrade_moves_bindings_into_rows_and_removes_only_companion_registry_records(
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
    hass.config_entries = ConfigEntries(hass, {})
    for config_entry in by_id.values():
        hass.config_entries._entries[config_entry.entry_id] = config_entry
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

    initialize_controllers(hass, entry)
    initialize_controllers(hass, entry)  # Reload must not duplicate the device list.

    assert entities.async_get(obsolete.entity_id) is None
    assert entities.async_get(battery.entity_id) is battery
    assert devices.async_get(hue.id) is hue
    assert devices.async_get(original.id) is None
    assert not dr.async_entries_for_config_entry(devices, entry.entry_id)
    assert len(entry.subentries) == 2
    migrated = next(s for s in entry.subentries.values() if s.unique_id == "dial-a")
    assert migrated.title == "My dial"
    assert controller_binding(entry, "dial-a")["enabled"] is True
    assert controller_binding(entry, "dial-a")["lights"] == ["light.test"]
    assert not er.async_entries_for_config_entry(entities, entry.entry_id)
    assert "controllers" not in entry.options
    hass.config_entries.async_remove_subentry(entry, migrated.subentry_id)
    initialize_controllers(hass, entry)
    assert len(entry.subentries) == 1
    assert controller_binding(entry, "dial-a") == {}
    await hass.async_stop()
