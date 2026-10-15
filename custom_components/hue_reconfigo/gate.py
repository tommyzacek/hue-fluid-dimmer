"""Optional shared state condition, independently enabled for controller families."""


def allows(hass, options, kind):
    if not options.get("motion_gate_enabled", False):
        return True
    if not options.get("gate_" + kind, kind == "motion"):
        return True
    state = hass.states.get(options.get("motion_gate_entity", ""))
    permitted = {s.strip() for s in options.get("motion_gate_states", "").split(",") if s.strip()}
    return bool(
        state and state.state not in ("unknown", "unavailable") and state.state in permitted
    )
