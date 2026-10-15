"""Explicit Hue controller models; no inference from user-assigned names."""

MODELS = {"ROM001": "button", "RDM003": "button", "RDM005": "button", "RWL022": "dimmer"}


def controller_kind(model):
    return MODELS.get(model)


class HoldDirections:
    """Thresholds at start only; direction is remembered per controller/button."""

    def __init__(self):
        self.previous = {}

    def choose(self, key, level, fixed=None):
        if fixed in ("up", "down"):
            direction = fixed
        elif level < 30:
            direction = "up"
        elif level > 60:
            direction = "down"
        else:
            direction = "down" if self.previous.get(key) == "up" else "up"
        self.previous[key] = direction
        return direction


def motion_service_role(entity_id, unique_id, services):
    """Hue enable switches share sensor resource IDs; never treat them as readings."""
    resource = unique_id.rsplit(":", 1)[-1]
    if entity_id.startswith("switch."):
        if resource == services.get("motion"):
            return "motion_enabled"
        if resource == services.get("light_level"):
            return "lux_enabled"
    if entity_id.startswith("binary_sensor.") and resource == services.get("motion"):
        return "motion"
    if entity_id.startswith("sensor.") and resource == services.get("light_level"):
        return "lux"
    return None
