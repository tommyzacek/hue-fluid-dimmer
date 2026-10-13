"""Diagnostics contain counters/settings only, never bridge credentials."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import HueFluidDimmerEntry
from .const import CONF_BINDINGS, CONF_HUE_ENTRY


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HueFluidDimmerEntry
) -> dict:
    runtime = entry.runtime_data
    return {
        "available": runtime.available,
        "controllers": len(runtime.resources),
        "requests": runtime.poll_count,
        "errors": runtime.error_count,
        "fresh_reports": runtime.report_count,
        "settings": async_redact_data(dict(entry.options), {CONF_BINDINGS}),
        "source": "configured official Hue entry" if entry.data.get(CONF_HUE_ENTRY) else "missing",
    }
