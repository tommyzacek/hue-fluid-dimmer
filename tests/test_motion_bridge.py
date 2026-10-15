from unittest.mock import AsyncMock

from custom_components.hue_fluid_dimmer import motion_bridge as bridge


async def test_save_unchanged_sensitivity_and_sync_off_does_not_write(monkeypatch):
    monkeypatch.setattr(bridge, "sensor_settings", AsyncMock(return_value=("motion", 2, 2)))
    request = AsyncMock()
    monkeypatch.setattr(bridge, "request", request)
    await bridge.save_settings(
        None, "sensor", {}, {"enabled": True, "motion_sensitivity": 2, "motion_sync_bridge": False}
    )
    request.assert_not_awaited()


async def test_save_sensitivity_changes_actual_sensor_without_touching_rules(monkeypatch):
    monkeypatch.setattr(bridge, "sensor_settings", AsyncMock(return_value=("motion", 2, 2)))
    request = AsyncMock()
    monkeypatch.setattr(bridge, "request", request)
    await bridge.save_settings(None, "sensor", {}, {"enabled": True, "motion_sensitivity": 1})
    request.assert_awaited_once_with(None, "motion", "motion", {"sensitivity": {"sensitivity": 1}})


async def test_disabled_control_never_reads_or_writes_bridge_on_save(monkeypatch):
    read = AsyncMock()
    request = AsyncMock()
    monkeypatch.setattr(bridge, "sensor_settings", read)
    monkeypatch.setattr(bridge, "request", request)
    await bridge.save_settings(
        None, "sensor", {}, {"enabled": False, "motion_sync_bridge": True, "motion_sensitivity": 0}
    )
    read.assert_not_awaited()
    request.assert_not_awaited()


async def test_legacy_sync_flag_never_writes_a_behavior_rule(monkeypatch):
    monkeypatch.setattr(bridge, "sensor_settings", AsyncMock(return_value=("motion", 2, 2)))
    request = AsyncMock()
    monkeypatch.setattr(bridge, "request", request)
    await bridge.save_settings(
        None,
        "sensor",
        {},
        {
            "enabled": True,
            "motion_sensitivity": 1,
            "motion_sync_bridge": True,
            "motion_lux": 0,
            "motion_use_lux": True,
        },
    )
    request.assert_awaited_once_with(None, "motion", "motion", {"sensitivity": {"sensitivity": 1}})
