"""Hue Reconfigo companion integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import BridgeError
from .configuration import initialize_controllers, update_brand_title
from .runtime import Runtime

type HueFluidDimmerEntry = ConfigEntry[Runtime]


async def async_setup_entry(hass: HomeAssistant, entry: HueFluidDimmerEntry) -> bool:
    runtime = Runtime(hass, entry)
    try:
        await runtime.initialize()
    except BridgeError as err:
        raise ConfigEntryNotReady(str(err)) from err
    entry.runtime_data = runtime
    update_brand_title(hass, entry)
    initialize_controllers(hass, entry)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    runtime.start()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: HueFluidDimmerEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HueFluidDimmerEntry) -> bool:
    await entry.runtime_data.close()
    return True
