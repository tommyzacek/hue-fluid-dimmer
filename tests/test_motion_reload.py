from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.hue_fluid_dimmer import async_reload_entry


async def test_binding_save_preserves_live_timers():
    entry = SimpleNamespace(
        data={"bridge": "a"},
        options={"mode": "active"},
        entry_id="test",
        runtime_data=SimpleNamespace(reload_config=({"bridge": "a"}, {"mode": "active"})),
    )
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_reload=AsyncMock()))
    await async_reload_entry(hass, entry)
    hass.config_entries.async_reload.assert_not_awaited()
    entry.options = {"mode": "continuous"}
    await async_reload_entry(hass, entry)
    hass.config_entries.async_reload.assert_awaited_once_with("test")


async def test_save_restarts_only_changed_motion_with_new_binding(monkeypatch):
    import runpy

    from custom_components.hue_fluid_dimmer.runtime import Runtime

    setup = runpy.run_path("tests/test_motion_policies.py")["setup"]
    engine, states, call, binding = setup()
    binding["motion_timeout"] = 300
    await engine.update("bath", binding, True)
    await engine.update("kitchen", binding, True)
    old_bath = engine.sessions["bath"]
    kitchen = engine.sessions["kitchen"]
    old_bath["blocked"].add("light.a")
    engine.overrides["bath"] = {"light.a": {"return": "off"}}
    states["binary_sensor.bath"] = SimpleNamespace(state="on")
    fresh = {**binding, "motion_timeout": 60}
    monkeypatch.setattr(
        "custom_components.hue_fluid_dimmer.runtime.controller_binding",
        lambda entry, resource: dict(fresh),
    )
    runtime = object.__new__(Runtime)
    runtime.motion, runtime.hass, runtime.entry = engine, engine.hass, None
    runtime.motion_entities = {"binary_sensor.bath": "bath"}
    runtime.control_devices = {"bath": {}}
    await runtime.reconfigure_motion("bath")
    assert engine.sessions["kitchen"] is kitchen
    assert engine.sessions["bath"] is not old_bath
    assert engine.sessions["bath"]["binding"]["motion_timeout"] == 60
    assert not engine.sessions["bath"]["blocked"]
    assert "bath" not in engine.overrides
    states["binary_sensor.bath"].state = "off"
    await runtime.reconfigure_motion("bath")
    assert "bath" not in engine.sessions
    assert engine.sessions["kitchen"] is kitchen
