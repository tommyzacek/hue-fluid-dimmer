"""Admin-only controller overview; reuse Home Assistant's configuration dialogs."""

from pathlib import Path

import probatio as p
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback

from .const import DOMAIN, SUBENTRY_TAP_DIAL

PANEL_PATH = "hue-reconfigo"


def describe_entries(entries):
    """Expose only names, identifiers and grouping metadata, never bindings/credentials."""
    bridges = []
    for entry in entries:
        controls = []
        for sub in entry.subentries.values():
            if sub.subentry_type != SUBENTRY_TAP_DIAL:
                continue
            family = sub.data.get("controller_kind", "tap_dial")
            controls.append(
                {
                    "subentry_id": sub.subentry_id,
                    "subentry_type": sub.subentry_type,
                    "title": sub.title,
                    "family": "dial" if family == "tap_dial" else family,
                    "enabled": bool(sub.data.get("enabled", False)),
                }
            )
        bridges.append(
            {
                "entry_id": entry.entry_id,
                "domain": DOMAIN,
                "title": entry.title,
                "supported_subentry_types": {SUBENTRY_TAP_DIAL: {"supports_reconfigure": True}},
                "controllers": controls,
            }
        )
    return bridges


@websocket_api.websocket_command({p.Required("type"): "hue_reconfigo/overview"})
@websocket_api.require_admin
@callback
def websocket_overview(hass, connection, msg):
    connection.send_result(msg["id"], describe_entries(hass.config_entries.async_entries(DOMAIN)))


async def async_setup_panel(hass):
    if not hass.data.get("hrc_overview_api"):
        websocket_api.async_register_command(hass, websocket_overview)
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/hue_reconfigo/overview.js",
                    str(Path(__file__).parent / "frontend" / "overview.js"),
                    False,
                )
            ]
        )
        hass.data["hrc_overview_api"] = True
    if not hass.data.get("hrc_overview_panel"):
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_PATH,
            webcomponent_name="hrc-controller-overview",
            sidebar_title="Hue Reconfigo",
            sidebar_icon="mdi:tune-variant",
            module_url="/hue_reconfigo/overview.js?v=2",
            require_admin=True,
        )
        hass.data["hrc_overview_panel"] = True


def async_unload_panel(hass, entry):
    if not any(
        e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED
        for e in hass.config_entries.async_entries(DOMAIN)
    ):
        frontend.async_remove_panel(hass, PANEL_PATH)
        hass.data.pop("hrc_overview_panel", None)
