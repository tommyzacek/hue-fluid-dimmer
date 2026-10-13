"""Dial profiles and shared light selections."""

PROFILES = {"gentle": (0.75, 1.0), "balanced": (1.5, 1.0), "swift": (3.0, 0.5)}


def targets(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    return list(value or [])


def light_targets(value) -> list[str]:
    selected = targets(value)
    return selected if all(item.startswith("light.") for item in selected) else []


def resolve_binding(binding: dict) -> dict:
    result = dict(binding)
    source = result.get("dial_source", "custom")
    if source != "custom":
        result["lights"] = light_targets(result.get(source))
    return result


def form_values(binding: dict) -> dict:
    profile = binding.get("dial_profile")
    if profile is None:
        pair = (binding.get("sensitivity", 1.5), binding.get("transition", 1.0))
        profile = next((key for key, value in PROFILES.items() if value == pair), "custom")
    return {
        "enabled": binding.get("enabled", False),
        "dial": {
            "profile": profile,
            "source": binding.get("dial_source", "custom"),
            "lights": binding.get("lights", []),
            "sensitivity": binding.get("custom_sensitivity", binding.get("sensitivity", 1.5)),
            "transition": binding.get("custom_transition", binding.get("transition", 1.0)),
        },
        **{f"button_{i}": {"targets": targets(binding.get(f"button_{i}"))} for i in range(1, 5)},
    }


def parse_form(values: dict) -> tuple[dict, str | None]:
    """Flatten the form, preserving custom values independently of the preset."""
    dial = values["dial"]
    sensitivity, transition = PROFILES.get(
        dial["profile"], (dial["sensitivity"], dial["transition"])
    )
    result = {
        "enabled": values["enabled"],
        "dial_profile": dial["profile"],
        "dial_source": dial["source"],
        "custom_sensitivity": dial["sensitivity"],
        "custom_transition": dial["transition"],
        "sensitivity": sensitivity,
        "transition": transition,
        "lights": dial.get("lights", []),
    }
    for index in range(1, 5):
        field = f"button_{index}"
        selected = targets(values.get(field, {}).get("targets"))
        if selected:
            if not light_targets(selected) and not (
                len(selected) == 1 and selected[0].split(".", 1)[0] in ("scene", "script")
            ):
                return result, "button_targets_invalid"
            result[field] = selected
    if result["enabled"]:
        if result["dial_source"] != "custom" and not light_targets(
            result.get(result["dial_source"])
        ):
            return result, "button_lights_only"
        if not resolve_binding(result).get("lights"):
            return result, "lights_required"
    return result, None
