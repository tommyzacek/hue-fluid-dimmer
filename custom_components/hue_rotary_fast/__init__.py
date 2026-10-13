"""Hue Rotary Fast companion integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import BridgeError
from .runtime import Runtime

type HueRotaryEntry = ConfigEntry[Runtime]
PLATFORMS = [Platform.EVENT]


async def async_setup_entry(hass: HomeAssistant, entry: HueRotaryEntry) -> bool:
    runtime = Runtime(hass, entry)
    try:
        await runtime.initialize()
    except BridgeError as err:
        raise ConfigEntryNotReady(str(err)) from err
    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    runtime.start()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: HueRotaryEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HueRotaryEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.close()
        return True
    return False
