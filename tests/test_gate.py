from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_runtime import make_runtime

from custom_components.hue_reconfigo.gate import allows


def test_gate_families_are_independent_and_old_motion_settings_migrate():
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda _: SimpleNamespace(state="pryč")))
    options = {
        "motion_gate_enabled": True,
        "motion_gate_entity": "sensor.house",
        "motion_gate_states": "doma",
    }
    assert not allows(hass, options, "motion")
    for kind in ("button", "dial", "dimmer"):
        assert allows(hass, options, kind)
        options["gate_" + kind] = True
        assert not allows(hass, options, kind)
        options["gate_" + kind] = False
    options["gate_motion"] = False
    assert allows(hass, options, "motion")
    options["motion_gate_enabled"] = False
    options["gate_dial"] = True
    assert allows(hass, options, "dial")


@pytest.mark.parametrize("kind", ["button", "dial", "tap_dial", "dimmer"])
async def test_blocked_controller_cannot_execute_press_hold_or_rotation(monkeypatch, kind):
    binding = {
        "enabled": True,
        "controller_kind": kind,
        "lights": ["light.one"],
        "button_1": {"short": ["light.one"], "long": ["light.one"], "long_mode": "dimming"},
    }
    runtime, _ = make_runtime(
        monkeypatch,
        {
            "controllers": {"one": binding},
            "motion_gate_enabled": True,
            "motion_gate_entity": "sensor.house",
            "motion_gate_states": "doma",
            "gate_" + ("dial" if kind == "tap_dial" else kind): True,
        },
    )
    runtime.hass.states = SimpleNamespace(get=lambda _: SimpleNamespace(state="pryč"))
    runtime.dimmer.rotate = Mock()
    runtime.dimmer.button_step = Mock()
    await runtime.button("one", binding, 1)
    runtime.button_hold_event("one", 1, "start", 1)
    runtime.button_hold_event("one", 1, "repeat", 2)
    runtime.rotate_dial("one", binding, 15)
    runtime.dimmer.rotate.assert_not_called()
    runtime.dimmer.button_step.assert_not_called()
    assert not runtime.action_tasks and not runtime.button_ramp_states
    await runtime.close()
