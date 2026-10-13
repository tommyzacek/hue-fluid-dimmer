"""Hue Fluid Dimmer companion integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .api import BridgeError
from .const import DOMAIN
from .runtime import Runtime

type HueFluidDimmerEntry = ConfigEntry[Runtime]


def register_controllers(hass: HomeAssistant, entry: HueFluidDimmerEntry) -> None:
    """Keep the controller list without exposing extra entities."""
    devices = dr.async_get(hass)
    controllers = entry.runtime_data.controllers()
    for resource in entry.runtime_data.resources:
        if resource.get("id") not in controllers:
            continue
        devices.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, resource["owner"]["rid"])},
            name=controllers[resource["id"]],
            manufacturer="Signify",
            model="Hue rotary controller",
            configuration_url=(
                f"homeassistant://config/integrations/integration/{DOMAIN}"
                f"#config_entry={entry.entry_id}"
            ),
        )

    # Upgrade from 0.1.1: remove only this entry's obsolete event entities.
    # Its device records and controller options remain intact.
    entities = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entities, entry.entry_id):
        if entity.platform == DOMAIN and entity.domain == "event":
            entities.async_remove(entity.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: HueFluidDimmerEntry) -> bool:
    runtime = Runtime(hass, entry)
    try:
        await runtime.initialize()
    except BridgeError as err:
        raise ConfigEntryNotReady(str(err)) from err
    entry.runtime_data = runtime
    register_controllers(hass, entry)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    runtime.start()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: HueFluidDimmerEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HueFluidDimmerEntry) -> bool:
    await entry.runtime_data.close()
    return True
