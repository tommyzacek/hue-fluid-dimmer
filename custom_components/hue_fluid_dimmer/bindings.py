"""Dial profiles and shared light selections."""

GESTURES = ("short", "long", "double", "triple")


def button_actions(binding: dict, index: int) -> dict:
    """Read new actions, including legacy short-release targets."""
    value = binding.get(f"button_{index}", {})
    if isinstance(value, dict):
        actions = {key: targets(value.get(key)) for key in GESTURES if value.get(key)}
        if value.get("long_operation") == "dial":
            actions["long"] = targets(value.get("short"))
        return actions
    return {"short": targets(value)} if value else {}


def button_long_mode(binding: dict, index: int) -> tuple[str, str]:
    value = binding.get(f"button_{index}", {})
    if not isinstance(value, dict):
        return "action", "up"
    return value.get("long_mode", "action"), "up"


def button_operation(binding: dict, index: int, action: str) -> tuple[str, float]:
    value = binding.get(f"button_{index}", {})
    if not isinstance(value, dict):
        return "toggle", 100.0
    if action == "long" and value.get("long_mode") == "dimming":
        return "dimming", 100.0
    return value.get(f"{action}_operation", "toggle"), value.get(f"{action}_percentage", 100.0)


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
    if result.get("dial_linked"):
        selected = button_actions(result, 1).get("short", [])
        result["lights"] = selected if percentage_targets(selected) else []
        return result
    source = result.get("dial_source", "custom")
    if source != "custom":
        result["lights"] = light_targets(button_actions(result, int(source[-1])).get("short"))
    return result


def percentage_targets(selected) -> bool:
    return bool(selected) and (
        all(item.startswith("light.") for item in selected)
        or all(item.startswith(("fan.", "number.")) for item in selected)
    )


def link_main_binding(binding: dict) -> dict:
    """Preserve a legacy dial target as button 1's target when it had none."""
    result = dict(binding)
    if result.get("dial_linked"):
        return result
    previous = resolve_binding(result).get("lights", [])
    old = result.get("button_1", {})
    button = dict(old) if isinstance(old, dict) else {"short": targets(old)}
    if not button.get("short") and percentage_targets(previous):
        button["short"] = previous
        result["button_1"] = button
    result["dial_linked"] = True
    return result


def form_values(binding: dict) -> dict:
    binding = link_main_binding(binding)
    profile = binding.get("dial_profile")
    if profile is None:
        pair = (binding.get("sensitivity", 1.5), binding.get("transition", 1.0))
        profile = next((key for key, value in PROFILES.items() if value == pair), "custom")
    return {
        "enabled": binding.get("enabled", False),
        "dial": {
            "profile": profile,
            "adaptive_transition": binding.get("adaptive_transition", False),
            "nonlight_sensitivity": binding.get("custom_nonlight_sensitivity", 1.5),
            "sensitivity": binding.get("custom_sensitivity", binding.get("sensitivity", 1.5)),
            "transition": binding.get("custom_transition", binding.get("transition", 1.0)),
            "nonlight_transition": binding.get(
                "custom_nonlight_transition", binding.get("transition", 1.0)
            ),
        },
        **{
            f"button_{i}": {
                **{
                    f"{action}_enabled": action in button_actions(binding, i) for action in GESTURES
                },
                **{
                    f"{action}_targets": button_actions(binding, i).get(action, [])
                    for action in GESTURES
                },
                **{
                    f"{action}_operation": button_operation(binding, i, action)[0]
                    for action in GESTURES
                },
                **{
                    f"{action}_percentage": button_operation(binding, i, action)[1]
                    for action in GESTURES
                },
            }
            for i in range(1, 5)
        },
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
        "adaptive_transition": dial.get("adaptive_transition", False),
        "dial_linked": True,
        "custom_sensitivity": dial["sensitivity"],
        "custom_transition": dial["transition"],
        "custom_nonlight_sensitivity": dial.get("nonlight_sensitivity", 1.5),
        "nonlight_sensitivity": PROFILES.get(
            dial["profile"], (dial.get("nonlight_sensitivity", 1.5), 0)
        )[0],
        "sensitivity": sensitivity,
        "transition": transition,
        "custom_nonlight_transition": dial.get("nonlight_transition", dial["transition"]),
        "nonlight_transition": {"gentle": 1.0, "balanced": 0.75, "swift": 0.5}.get(
            dial["profile"], dial.get("nonlight_transition", dial["transition"])
        ),
    }
    for index in range(1, 5):
        field = f"button_{index}"
        actions = {}
        section = values.get(field, {})
        long_dimming = section.get("long_operation") == "dimming" or (
            "long_operation" not in section and section.get("long_mode") == "dimming"
        )
        for action in GESTURES:
            if not section.get(f"{action}_enabled", False):
                continue
            operation = section.get(f"{action}_operation", "toggle")
            if action == "long" and operation == "dial":
                selected = (
                    targets(section.get("short_targets")) if section.get("short_enabled") else []
                )
                if index == 1 or not percentage_targets(selected):
                    return result, "dial_target_required"
                actions["long"] = selected
                actions["long_operation"] = "dial"
                continue
            selected = targets(section.get(f"{action}_targets"))
            if not selected:
                return result, "button_target_required"
            percentage_target = (
                action == "long"
                and long_dimming
                and (
                    bool(light_targets(selected))
                    or all(item.startswith(("fan.", "number.")) for item in selected)
                )
            )
            numeric_target = all(item.startswith("number.") for item in selected)
            fan_target = all(item.startswith("fan.") for item in selected)
            if (
                not percentage_target
                and not numeric_target
                and not fan_target
                and not light_targets(selected)
                and not (len(selected) == 1 and selected[0].split(".", 1)[0] in ("scene", "script"))
            ):
                return result, "button_targets_invalid"
            actions[action] = selected
            if not (action == "long" and long_dimming):
                operation = section.get(f"{action}_operation", "toggle")
                percentage = section.get(f"{action}_percentage", 100.0)
                if (
                    operation not in ("toggle", "previous", "configured")
                    or not isinstance(percentage, (int, float))
                    or not 0 < percentage <= 100
                ):
                    return result, "button_percentage_invalid"
                # Keep legacy bindings compact while preserving explicit numeric on levels.
                if operation != "toggle" or numeric_target:
                    actions[f"{action}_operation"] = operation
                    actions[f"{action}_percentage"] = percentage
        if "long" in actions:
            mode = "dimming" if long_dimming else "action"
            if mode == "dimming" and not (
                light_targets(actions["long"])
                or all(item.startswith(("fan.", "number.")) for item in actions["long"])
            ):
                return result, "button_percentage_only"
            actions["long_mode"] = mode
        if actions:
            result[field] = actions
    if result["enabled"]:
        main = button_actions(result, 1).get("short", [])
        if main and not percentage_targets(main):
            return result, "dial_target_required"
        if not main and any(
            result.get(f"button_{index}", {}).get("long_operation") == "dial"
            for index in range(2, 5)
        ):
            return result, "dial_target_required"
        if not resolve_binding(result).get("lights") and not any(
            button_actions(result, index) for index in range(1, 5)
        ):
            return result, "lights_required"
    return result, None
