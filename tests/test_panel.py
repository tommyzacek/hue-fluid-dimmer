from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.exceptions import Unauthorized

from custom_components.hue_fluid_dimmer.panel import describe_entries, websocket_overview


def test_overview_exports_only_identifiers_titles_family_and_enable_state():
    entries = [
        SimpleNamespace(
            entry_id="bridge-a",
            title="Hue Reconfigo – Bridge A",
            subentries={
                "one": SimpleNamespace(
                    subentry_id="one",
                    subentry_type="tap_dial",
                    title="Kitchen Dial",
                    data={
                        "controller_kind": "tap_dial",
                        "enabled": True,
                        "secret": "must-not-leak",
                        "lights": ["light.private"],
                    },
                ),
                "two": SimpleNamespace(
                    subentry_id="two",
                    subentry_type="tap_dial",
                    title="Motion",
                    data={"controller_kind": "motion", "enabled": False},
                ),
                "other": SimpleNamespace(
                    subentry_id="other", subentry_type="other", title="Unrelated", data={}
                ),
            },
        )
    ]
    result = describe_entries(entries)
    assert len(result) == 1
    controls = result[0]["controllers"]
    assert [c["family"] for c in controls] == ["dial", "motion"]
    assert controls[0]["enabled"] and not controls[1]["enabled"]
    assert "must-not-leak" not in str(result) and "light.private" not in str(result)
    assert "data" not in controls[0]


def test_overview_api_requires_admin():
    with pytest.raises(Unauthorized):
        websocket_overview(
            SimpleNamespace(),
            SimpleNamespace(user=SimpleNamespace(is_admin=False)),
            {"id": 1, "type": "hue_fluid_dimmer/overview"},
        )


def test_overview_api_uses_current_entries():
    connection = SimpleNamespace(user=SimpleNamespace(is_admin=True), send_result=Mock())
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda domain: []))
    websocket_overview(hass, connection, {"id": 10, "type": "hue_fluid_dimmer/overview"})
    connection.send_result.assert_called_once_with(10, [])


async def test_overview_does_not_replace_bridge_options_dialog(monkeypatch):
    from unittest.mock import AsyncMock

    from custom_components.hue_fluid_dimmer import panel

    register = AsyncMock()
    monkeypatch.setattr(panel.panel_custom, "async_register_panel", register)
    hass = SimpleNamespace(data={"hfd_overview_api": True})
    await panel.async_setup_panel(hass)
    assert register.await_args.kwargs["require_admin"] is True
    assert "config_panel_domain" not in register.await_args.kwargs
