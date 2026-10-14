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
