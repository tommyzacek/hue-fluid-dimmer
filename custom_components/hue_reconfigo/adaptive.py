"""Optional Adaptive Lighting cooperation through entity state and public services."""

import logging

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


def members(hass, entity, seen=None):
    """Expand exposed light membership, guarding cycles and unknown members."""
    seen = set(seen or ())
    if entity in seen:
        return set()
    seen.add(entity)
    state = hass.states.get(entity)
    children = state.attributes.get("entity_id") if state else None
    if isinstance(children, str):
        children = [children]
    if not isinstance(children, (list, tuple)) or not children:
        return {entity}
    result = set()
    for child in children:
        if isinstance(child, str) and child.startswith("light."):
            result.update(members(hass, child, seen))
    return result


def matches(hass, selected, profiles):
    """Match each profile independently without broadening a partial group target."""
    selected = {entity for entity in selected if entity.startswith("light.")}
    expanded = set().union(*(members(hass, entity) for entity in selected)) if selected else set()
    result, partial = [], []
    for switch, configuration in profiles:
        lights = configuration.get("lights", [])
        if not isinstance(lights, list):
            continue
        matched = set()
        for entity in lights:
            if not isinstance(entity, str) or not entity.startswith("light."):
                continue
            group = members(hass, entity)
            if configuration.get("expand_light_groups", True):
                matched.update(group & expanded)
            elif entity in selected or (group and group <= expanded):
                matched.add(entity)
            elif group & expanded:
                partial.append((switch, entity))
        if matched:
            result.append((switch, sorted(matched)))
    return result, partial


class AdaptiveCooperation:
    def __init__(self, hass, enabled):
        self.hass, self.enabled = hass, enabled
        self.warned = set()

    def profiles(self):
        registry = er.async_get(self.hass)
        profiles = []
        for entity in registry.entities.values():
            if entity.platform != "adaptive_lighting" or not entity.entity_id.startswith("switch."):
                continue
            state = self.hass.states.get(entity.entity_id)
            if state is None or state.state != "on" or "configuration" not in state.attributes:
                continue
            # The optional state attribute can be empty by default. Read the
            # documented configuration fields via HA's config-entry API instead.
            configuration = state.attributes.get("configuration") or {}
            if entity.config_entry_id:
                entry = self.hass.config_entries.async_get_entry(entity.config_entry_id)
                if entry:
                    configuration = {**entry.data, **entry.options, **configuration}
            if "lights" in configuration:
                profiles.append((entity.entity_id, configuration))
        return profiles

    async def mark(self, selected, component="brightness"):
        if not self.enabled() or not self.hass.services.has_service(
            "adaptive_lighting", "set_manual_control"
        ):
            return
        profiles = self.profiles()
        resolved, partial = matches(self.hass, selected, profiles)
        for pair in partial:
            if pair not in self.warned:
                self.warned.add(pair)
                _LOGGER.warning(
                    "Cannot mark only part of Adaptive Lighting group %s (%s); enable "
                    "expand_light_groups in that profile or control the whole group",
                    pair[1],
                    pair[0],
                )
        for switch, lights in resolved:
            state = self.hass.states.get(switch)
            brightness = set(
                state.attributes.get(
                    "manual_control_brightness", state.attributes.get("manual_control", [])
                )
            )
            color = set(state.attributes.get("manual_control_color", []))
            groups = {}
            for light in lights:
                want_brightness = component in ("brightness", "both") or light in brightness
                want_color = component in ("color", "both") or light in color
                if (not want_brightness or light in brightness) and (
                    not want_color or light in color
                ):
                    continue
                mode = True if want_brightness and want_color else component
                groups.setdefault(mode, []).append(light)
            for mode, pending in groups.items():
                data = {"entity_id": switch, "lights": pending, "manual_control": mode}
                try:
                    try:
                        await self.hass.services.async_call(
                            "adaptive_lighting", "set_manual_control", data, blocking=True
                        )
                    except ServiceValidationError:
                        data["manual_control"] = True
                        await self.hass.services.async_call(
                            "adaptive_lighting", "set_manual_control", data, blocking=True
                        )
                except HomeAssistantError as err:
                    _LOGGER.warning("Unable to mark Adaptive Lighting manual control: %s", err)

    async def pause(self, selected):
        """Temporarily protect automatic motion warning; preserve existing manual flags."""
        if not self.enabled() or not self.hass.services.has_service(
            "adaptive_lighting", "set_manual_control"
        ):
            return []
        resolved, _ = matches(self.hass, selected, self.profiles())
        leases = []
        for switch, lights in resolved:
            state = self.hass.states.get(switch)
            prior = set(
                state.attributes.get(
                    "manual_control_brightness", state.attributes.get("manual_control", [])
                )
            )
            pending = [entity for entity in lights if entity not in prior]
            if not pending:
                continue
            prior_color = set(state.attributes.get("manual_control_color", []))
            for has_color in (False, True):
                subset = [entity for entity in pending if (entity in prior_color) == has_color]
                if not subset:
                    continue
                # The public service replaces flags: preserve color per light.
                data = {
                    "entity_id": switch,
                    "lights": subset,
                    "manual_control": True if has_color else "brightness",
                }
                legacy = False
                try:
                    try:
                        await self.hass.services.async_call(
                            "adaptive_lighting", "set_manual_control", data, blocking=True
                        )
                    except ServiceValidationError:
                        legacy = True
                        data["manual_control"] = True
                        await self.hass.services.async_call(
                            "adaptive_lighting", "set_manual_control", data, blocking=True
                        )
                    leases.append((switch, subset, legacy))
                except HomeAssistantError as err:
                    _LOGGER.warning(
                        "Unable to protect motion warning from Adaptive Lighting: %s", err
                    )
        return leases

    async def release(self, leases):
        if not self.hass.services.has_service("adaptive_lighting", "set_manual_control"):
            return
        for switch, lights, legacy in leases:
            state = self.hass.states.get(switch)
            if state is None:
                continue
            color = state.attributes.get("manual_control_color", [])
            # Preserve a color override introduced while our warning was active.
            selected = [entity for entity in lights if legacy or entity not in color]
            if selected:
                try:
                    await self.hass.services.async_call(
                        "adaptive_lighting",
                        "set_manual_control",
                        {"entity_id": switch, "lights": selected, "manual_control": False},
                        blocking=True,
                    )
                except HomeAssistantError as err:
                    _LOGGER.warning("Unable to release motion Adaptive Lighting pause: %s", err)
