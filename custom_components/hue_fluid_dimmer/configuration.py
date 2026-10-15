"""Controller configuration rows, independent of HA devices and entities."""

from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .bindings import link_main_binding, resolve_binding
from .const import (
    CONF_BINDINGS,
    CONF_CONTROLLERS_INITIALIZED,
    CONF_RESOURCE,
    DOMAIN,
    SUBENTRY_TAP_DIAL,
)


def controller_binding(entry: ConfigEntry, resource_id: str) -> dict:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_TAP_DIAL and subentry.unique_id == resource_id:
            return resolve_binding(link_main_binding(dict(subentry.data)))
    return {}


@callback
def initialize_controllers(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Bootstrap configuration rows and migrate the old companion registry records."""
    devices = dr.async_get(hass)
    controllers = entry.runtime_data.controllers()
    legacy = entry.options.get(CONF_BINDINGS, {})
    controls = getattr(entry.runtime_data, "control_devices", {})
    seen = set(entry.data.get("discovered_button_controllers", []))
    bootstrap = not entry.data.get(CONF_CONTROLLERS_INITIALIZED)
    candidates = (controllers.keys() | legacy.keys()) if bootstrap else controls.keys() - seen
    resources = {item["id"]: item for item in entry.runtime_data.resources if item.get("id")}
    for resource_id in candidates:
        if any(sub.unique_id == resource_id for sub in entry.subentries.values()):
            continue
        resource = resources.get(resource_id, {})
        old_device = devices.async_get_device_by_identifier(
            (DOMAIN, resource.get("owner", {}).get("rid", "")), entry.entry_id
        )
        title = (
            old_device.name_by_user
            if old_device and old_device.name_by_user
            else controllers.get(resource_id, resource_id)
        )
        model = controls.get(resource_id, {})
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                subentry_type=SUBENTRY_TAP_DIAL,
                unique_id=resource_id,
                title=title,
                data=MappingProxyType(
                    {
                        CONF_RESOURCE: resource_id,
                        "controller_kind": model.get("kind", "tap_dial"),
                        "controller_model": model.get("model"),
                        **legacy.get(resource_id, {}),
                    }
                ),
            ),
        )
    discovered = sorted(seen | controls.keys())
    if bootstrap or discovered != sorted(seen):
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_CONTROLLERS_INITIALIZED: True,
                "discovered_button_controllers": discovered,
            },
            options={key: value for key, value in entry.options.items() if key != CONF_BINDINGS},
        )

    # Only records owned by this companion are removed. Official Hue stays intact.
    entities = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entities, entry.entry_id):
        if entity.platform == DOMAIN and entity.domain == "event":
            entities.async_remove(entity.entity_id)
    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        if any(domain == DOMAIN for domain, _ in device.identifiers):
            devices.async_remove_device(device.id)


def update_brand_title(hass, entry):
    """Rename only the old generated title; preserve user titles and configuration."""
    prefix = "Hue Fluid Dimmer – "
    if entry.title.startswith(prefix):
        hass.config_entries.async_update_entry(
            entry, title="Hue Reconfigo – " + entry.title[len(prefix) :]
        )
