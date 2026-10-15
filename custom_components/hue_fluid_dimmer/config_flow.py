"""Select an existing Hue bridge and configure all its controllers in the GUI."""

from typing import Any

import probatio as p
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .api import BridgeError
from .bindings import GESTURES, form_values, parse_form
from .const import (
    CONF_HUE_ENTRY,
    CONF_INTERVAL,
    CONF_MODE,
    CONF_RESOURCE,
    CONF_WINDOW,
    DEFAULT_INTERVAL,
    DEFAULT_WINDOW,
    DOMAIN,
    HUE_DOMAIN,
    MODE_ACTIVE,
    MODE_CONTINUOUS,
    SUBENTRY_TAP_DIAL,
)
from .motion import DEFAULTS as MOTION_DEFAULTS
from .motion import START_DEFAULTS, parse_motion
from .motion_bridge import save_settings, sensor_settings
from .motion_schedule import periods_for, validate_periods


def select(options: dict[str, str]) -> selector.SelectSelector:
    return selector.SelectSelector(
        {"options": [{"value": value, "label": label} for value, label in options.items()]}
    )


def number(minimum: float, maximum: float, step: float) -> selector.NumberSelector:
    return selector.NumberSelector({"min": minimum, "max": maximum, "step": step, "mode": "box"})


class VisibleNumber(selector.NumberSelector):
    def serialize(self):
        config = super().serialize()["selector"]["number"]
        return {
            "selector": {"hfd_number": config},
            "visible": {"field": "profile", "value": "custom"},
        }


class ControllerEnabled(selector.BooleanSelector):
    def serialize(self):
        return {"selector": {"hfd_control_enabled": {}}}


class VisibleCustomBoolean(selector.BooleanSelector):
    def serialize(self):
        return {**super().serialize(), "visible": {"field": "profile", "value": "custom"}}


class CustomHeading(selector.ConstantSelector):
    """Display a static heading only for the custom dial profile."""

    def serialize(self):
        return {"selector": {"hfd_heading": {}}, "visible": {"field": "profile", "value": "custom"}}


class VisibleLights(selector.EntitySelector):
    def serialize(self):
        return {**super().serialize(), "visible": {"field": "source", "value": "custom"}}


class DialTargets(selector.EntitySelector):
    def __init__(self):
        super().__init__({"domain": ["light", "fan", "number"], "multiple": True})

    def serialize(self):
        return {**super().serialize(), "visible": {"field": "override", "value": True}}


class VisibleActionTargets(selector.EntitySelector):
    def __init__(self, action: str, kind="tap_dial"):
        domains = ["light", "script", "fan", "number"]
        super().__init__({"domain": domains, "multiple": True})
        self.action = action
        self.kind = kind

    def serialize(self):
        conditions = [{"field": f"{self.action}_enabled", "value": True}]
        if self.kind != "tap_dial":
            conditions.append({"field": f"{self.action}_other_targets", "value": True})
        return {
            **super().serialize(),
            "visible": conditions[0] if len(conditions) == 1 else conditions,
        }


class OtherTargets(selector.BooleanSelector):
    def __init__(self, action):
        super().__init__()
        self.action = action

    def serialize(self):
        conditions = [{"field": f"{self.action}_enabled", "value": True}]
        return {**super().serialize(), "visible": conditions}


class VisibleOperation(selector.ObjectSelector):
    def __init__(self, action, index=2, kind="tap_dial", selected=None, shared=None):
        super().__init__()
        self.action, self.index, self.kind = action, index, kind
        self.selected, self.shared = selected or [], shared or []
        self.options = ["toggle", "previous", "configured", "on", "off"]
        if action == "short" and kind == "dimmer" and index in (2, 3):
            self.options.extend(["step_up", "step_down"])
        if action == "long":
            self.options.append("dimming")
        if kind == "tap_dial" and index > 1:
            self.options.append("dial")

    def __call__(self, value):
        operation = value.get("operation") if isinstance(value, dict) else value
        if operation not in self.options:
            raise p.Invalid("invalid button action")
        return value

    def serialize(self):
        return {
            "selector": {
                "hfd_button_action": {
                    "options": self.options,
                    "action": self.action,
                    "index": self.index,
                    "kind": self.kind,
                    "targets": self.selected,
                    "shared": self.shared,
                }
            },
            "visible": {"field": f"{self.action}_enabled", "value": True},
        }


class VisiblePercentage(selector.NumberSelector):
    def __init__(self, action):
        super().__init__({"min": 1, "max": 100, "step": 1, "mode": "box"})
        self.action = action

    def serialize(self):
        return {
            "selector": {"hfd_brightness": {}},
            "visible": {"field": f"{self.action}_operation", "value": "configured"},
        }


def controller_form(values):
    return parse_motion(values) if values.get("controller_kind") == "motion" else parse_form(values)


class MotionLux(selector.NumberSelector):
    def __init__(self, entity=None, enabled_entity=None):
        super().__init__({"min": 0, "max": 660, "step": 1, "mode": "slider"})
        self.entity = entity
        self.enabled_entity = enabled_entity

    def serialize(self):
        return {
            "selector": {"hfd_lux": {"entity": self.entity, "enabled_entity": self.enabled_entity}}
        }


class MotionTimeout(selector.NumberSelector):
    def __init__(self):
        super().__init__({"min": 60, "max": 3600, "step": 30, "mode": "slider"})

    def __call__(self, value):
        result = super().__call__(value)
        if result % (30 if result <= 600 else 60):
            raise p.Invalid(
                "timeout must use 30-second steps up to 10 minutes and minute steps above"
            )
        return result

    def serialize(self):
        return {"selector": {"hfd_timeout": {}}}


class MotionPeriods(selector.ObjectSelector):
    def __call__(self, value):
        try:
            return validate_periods(value, parse_motion)
        except ValueError as err:
            raise p.Invalid(str(err)) from err

    def serialize(self):
        return {"selector": {"hfd_motion_periods": {}}}


class MotionSensitivity(selector.NumberSelector):
    def __init__(self):
        super().__init__({"min": 0, "max": 2, "step": 1, "mode": "slider"})

    def serialize(self):
        return {"selector": {"hfd_sensitivity": {}}}


class MotionEnabled(selector.BooleanSelector):
    def __init__(self, entity=None):
        super().__init__()
        self.entity = entity

    def serialize(self):
        return {"selector": {"hfd_motion_enabled": {"entity": self.entity}}}


class MotionEndMode(selector.SelectSelector):
    def __init__(self):
        super().__init__(
            {
                "options": ["half", "fade", "half_quick"],
                "translation_key": "motion_end_mode",
                "mode": "dropdown",
            }
        )

    def serialize(self):
        return {**super().serialize(), "visible": {"field": "motion_soft_end", "value": True}}


class StartupPercentage(selector.NumberSelector):
    def serialize(self):
        return {**super().serialize(), "visible": {"field": "brightness", "value": "configured"}}


class StartupTemperature(selector.ColorTempSelector):
    def __call__(self, value):
        return int(super().__call__(value) / 100 + 0.5) * 100

    def serialize(self):
        return {
            "selector": {"hfd_temperature": {}},
            "visible": {"field": "color", "value": "temperature"},
        }


class StartupColor(selector.ColorRGBSelector):
    def serialize(self):
        return {**super().serialize(), "visible": {"field": "color", "value": "rgb"}}


def startup_schema(values):
    values = {**START_DEFAULTS, **values}
    if values["brightness"] == "previous":
        values["brightness"] = "unchanged"
    return section(
        p.Schema(
            {
                p.Required("brightness", default=values["brightness"]): selector.SelectSelector(
                    {
                        "options": ["unchanged", "configured"],
                        "translation_key": "startup_brightness",
                        "mode": "dropdown",
                    }
                ),
                p.Required("percentage", default=values["percentage"]): StartupPercentage(
                    {"min": 1, "max": 100, "step": 1, "mode": "slider", "unit_of_measurement": "%"}
                ),
                p.Required("color", default=values["color"]): selector.SelectSelector(
                    {
                        "options": ["unchanged", "temperature", "rgb"],
                        "translation_key": "startup_color",
                        "mode": "dropdown",
                    }
                ),
                p.Required("temperature", default=values["temperature"]): StartupTemperature(
                    {"unit": "kelvin", "min": 1500, "max": 10000}
                ),
                p.Required("rgb", default=values["rgb"]): StartupColor(),
            }
        )
    )


class MotionBehavior(selector.ObjectSelector):
    def serialize(self):
        return {"selector": {"hfd_motion_behavior": {}}}


def behavior_schema(values):
    return MotionBehavior()


def motion_schema(old, submitted=None):
    values = {**MOTION_DEFAULTS, **old, **(submitted or {})}
    if "motion_soft_end" not in old and "motion_warning" in old:
        values["motion_soft_end"] = old["motion_warning"] > 0
    return p.Schema(
        {
            p.Required("enabled", default=values["enabled"]): MotionEnabled(
                values.get("_motion_enabled_entity")
            ),
            p.Required("motion_targets", default=values["motion_targets"]): selector.EntitySelector(
                {"domain": "light", "multiple": True}
            ),
            p.Required(
                "motion_lux_slider",
                default=values.get(
                    "motion_lux_slider",
                    min(values["motion_lux"], 650) if values["motion_use_lux"] else 660,
                ),
            ): MotionLux(values.get("_motion_lux_entity"), values.get("_lux_enabled_entity")),
            **(
                {
                    p.Required(
                        "motion_sensitivity", default=values["motion_sensitivity"]
                    ): MotionSensitivity()
                }
                if values["motion_sensitivity"] is not None
                else {}
            ),
            p.Required("motion_periods", default=periods_for(values)): MotionPeriods(),
            p.Required("motion_behavior", default=values["motion_behavior"]): behavior_schema(
                values["motion_behavior"]
            ),
            p.Required(
                "motion_soft_end", default=values["motion_soft_end"]
            ): selector.BooleanSelector(),
            p.Required("motion_end_mode", default=values["motion_end_mode"]): MotionEndMode(),
        }
    )


def binding_schema(old: dict, submitted: dict | None = None) -> p.Schema:
    if old.get("controller_kind") == "motion":
        return motion_schema(old, submitted)
    data = form_values(old)
    if submitted is not None:
        for field, value in submitted.items():
            if isinstance(value, dict) and isinstance(data.get(field), dict):
                data[field] = {**data[field], **value}
            else:
                data[field] = value
    kind = old.get("controller_kind", "tap_dial")
    dial = data["dial"]
    schema = {
        p.Required("enabled", default=data["enabled"]): ControllerEnabled(),
        p.Required("dial", default=data["dial"]): section(
            p.Schema(
                {
                    p.Required("override", default=dial["override"]): selector.BooleanSelector(),
                    p.Optional("targets", default=dial["targets"]): DialTargets(),
                    p.Required("profile", default=dial["profile"]): selector.SelectSelector(
                        {
                            "options": ["gentle", "balanced", "swift", "custom"],
                            "translation_key": "dial_profile",
                            "mode": "dropdown",
                        }
                    ),
                    p.Required(
                        "adaptive_transition", default=dial["adaptive_transition"]
                    ): VisibleCustomBoolean(),
                    p.Optional("lights_heading", default="lights"): CustomHeading(
                        {"value": "lights", "label": ""}
                    ),
                    p.Required("sensitivity", default=dial["sensitivity"]): VisibleNumber(
                        {"min": 0.1, "max": 10, "step": 0.05, "mode": "box"}
                    ),
                    p.Required("transition", default=dial["transition"]): VisibleNumber(
                        {
                            "min": 0.1,
                            "max": 3,
                            "step": 0.1,
                            "mode": "box",
                            "unit_of_measurement": "s",
                        }
                    ),
                    p.Optional("other_heading", default="other"): CustomHeading(
                        {"value": "other", "label": ""}
                    ),
                    p.Required(
                        "nonlight_sensitivity", default=dial["nonlight_sensitivity"]
                    ): VisibleNumber({"min": 0.1, "max": 10, "step": 0.05, "mode": "box"}),
                    p.Required(
                        "nonlight_transition", default=dial["nonlight_transition"]
                    ): VisibleNumber(
                        {
                            "min": 0.1,
                            "max": 3,
                            "step": 0.05,
                            "mode": "box",
                            "unit_of_measurement": "s",
                        }
                    ),
                }
            )
        ),
    }
    if kind != "tap_dial":
        schema = {
            p.Required("enabled", default=data["enabled"]): ControllerEnabled(),
            p.Required(
                "shared_targets", default=data.get("shared_targets", [])
            ): selector.EntitySelector({"domain": ["light", "fan", "number"], "multiple": True}),
        }
    for index in range(1, 2 if kind == "button" else 5):
        field = f"button_{index}"
        fields = {}
        for action in GESTURES:
            fields[p.Required(f"{action}_enabled", default=data[field][f"{action}_enabled"])] = (
                selector.BooleanSelector()
            )
            if kind != "tap_dial":
                fields[
                    p.Required(
                        f"{action}_other_targets", default=data[field][f"{action}_other_targets"]
                    )
                ] = OtherTargets(action)
            fields[p.Optional(f"{action}_targets", default=data[field][f"{action}_targets"])] = (
                VisibleActionTargets(action, kind)
            )
            operation = data[field][f"{action}_operation"]
            if not isinstance(operation, dict):
                operation = {
                    "operation": operation,
                    "percentage": data[field][f"{action}_percentage"],
                    "startup": data[field].get(
                        f"{action}_startup",
                        {
                            **START_DEFAULTS,
                            "brightness": "configured"
                            if operation == "configured"
                            else "unchanged",
                            "percentage": data[field][f"{action}_percentage"],
                        },
                    ),
                }
            data[field][f"{action}_operation"] = operation
            data[field].pop(f"{action}_percentage", None)
            data[field].pop(f"{action}_startup", None)
            fields[p.Required(f"{action}_operation", default=operation)] = VisibleOperation(
                action, index, kind, data[field][f"{action}_targets"], data.get("shared_targets")
            )
        schema[p.Optional(field, default=data[field])] = section(
            p.Schema(fields), {"collapsed": True}
        )
    return p.Schema(schema)


class HueFluidDimmerFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_TAP_DIAL: TapDialSubentryFlow}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HueFluidDimmerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        bridges = {
            entry.entry_id: entry.title
            for entry in self.hass.config_entries.async_entries(HUE_DOMAIN)
            if entry.data.get("api_version") == 2 and entry.state is ConfigEntryState.LOADED
        }
        if not bridges:
            return self.async_abort(reason="no_hue")
        if user_input is not None:
            entry_id = user_input[CONF_HUE_ENTRY]
            if entry_id not in bridges:
                return self.async_abort(reason="no_hue")
            await self.async_set_unique_id(entry_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Hue Reconfigo – {bridges[entry_id]}", data={CONF_HUE_ENTRY: entry_id}
            )
        return self.async_show_form(
            step_id="user", data_schema=p.Schema({p.Required(CONF_HUE_ENTRY): select(bridges)})
        )


class BridgeSettings(selector.ObjectSelector):
    def __call__(self, value):
        if not isinstance(value, dict):
            raise p.Invalid("Expected settings object")
        return p.Schema(
            {
                p.Required("motion_gate_enabled", default=False): bool,
                p.Required("gate_motion", default=True): bool,
                p.Required("gate_button", default=False): bool,
                p.Required("gate_dial", default=False): bool,
                p.Required("gate_dimmer", default=False): bool,
                p.Optional("motion_gate_entity", default=""): str,
                p.Optional("motion_gate_states", default=""): str,
                p.Required(CONF_MODE, default=MODE_ACTIVE): p.In((MODE_ACTIVE, MODE_CONTINUOUS)),
                p.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): p.All(
                    p.Coerce(float), p.Range(min=0.1, max=2)
                ),
                p.Required(CONF_WINDOW, default=DEFAULT_WINDOW): p.All(
                    p.Coerce(float), p.Range(min=1, max=10)
                ),
            }
        )(value)

    def serialize(self):
        return {"selector": {"hfd_bridge_settings": {}}}


class HueFluidDimmerOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self.async_step_polling(user_input)

    async def async_step_polling(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input = {**user_input, **user_input.get("bridge_settings", {})}
            user_input.pop("bridge_settings", None)
            if user_input.get("motion_gate_enabled") and (
                not user_input.get("motion_gate_entity")
                or not any(s.strip() for s in user_input.get("motion_gate_states", "").split(","))
                or any(
                    s.strip() in ("unknown", "unavailable")
                    for s in user_input.get("motion_gate_states", "").split(",")
                )
            ):
                errors["base"] = "motion_gate_required"
            else:
                return self.async_create_entry(
                    title="", data={**self.config_entry.options, **user_input}
                )
        options = {**self.config_entry.options, **(user_input or {})}
        settings = BridgeSettings()(
            {
                k: v
                for k, v in options.items()
                if k
                in (
                    "motion_gate_enabled",
                    "motion_gate_entity",
                    "motion_gate_states",
                    "gate_motion",
                    "gate_button",
                    "gate_dial",
                    "gate_dimmer",
                    CONF_MODE,
                    CONF_INTERVAL,
                    CONF_WINDOW,
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=p.Schema(
                {
                    p.Required(
                        "adaptive_lighting", default=options.get("adaptive_lighting", False)
                    ): selector.BooleanSelector(),
                    p.Required("bridge_settings", default=settings): BridgeSettings(),
                }
            ),
        )


class TapDialSubentryFlow(ConfigSubentryFlow):
    """Open a specific controller directly from its configuration row."""

    resource_id: str | None = None

    async def prepare_motion(self, old, resource):
        if old.get("controller_kind") != "motion":
            return old
        runtime = self._get_entry().runtime_data
        _, current, maximum = await sensor_settings(
            runtime.client, runtime.control_devices.get(resource, {})
        )
        return self.motion_metadata(
            {
                **old,
                "motion_sensitivity": round(current * 2 / maximum) if maximum else None,
            },
            resource,
        )

    def motion_metadata(self, old, resource):
        if old.get("controller_kind") != "motion":
            return old
        runtime = self._get_entry().runtime_data
        device = runtime.control_devices.get(resource, {})
        return {
            **old,
            "_motion_lux_entity": device.get("lux_entity"),
            "_motion_enabled_entity": device.get("motion_enabled_entity"),
            "_lux_enabled_entity": device.get("lux_enabled_entity"),
        }

    async def save_motion(self, binding, resource):
        if binding.get("controller_kind") == "motion":
            runtime = self._get_entry().runtime_data
            await save_settings(
                runtime.client, resource, runtime.control_devices.get(resource, {}), binding
            )

    def motion_context(self, binding, resource):
        if binding.get("controller_kind") != "motion":
            return {}
        device = self._get_entry().runtime_data.control_devices.get(resource, {})
        state = self.hass.states.get(device.get("lux_entity", ""))
        current = "—"
        try:
            current = f"{float(state.state):.1f}"
        except AttributeError, ValueError, TypeError:
            pass
        threshold = binding.get("motion_lux", MOTION_DEFAULTS["motion_lux"])
        rule = f"< {threshold:g} lx" if binding.get("motion_use_lux", False) else "∞"
        return {"motion_lux_current": current, "motion_lux_rule": rule}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        configured = {sub.unique_id for sub in entry.subentries.values()}
        controllers = {
            key: name
            for key, name in entry.runtime_data.controllers().items()
            if key not in configured
        }
        if not controllers:
            return self.async_abort(reason="no_unconfigured_controllers")
        if user_input is not None:
            self.resource_id = user_input["controller"]
            if self.resource_id not in controllers:
                return self.async_abort(reason="no_unconfigured_controllers")
            return await self.async_step_binding()
        return self.async_show_form(
            step_id="user", data_schema=p.Schema({p.Required("controller"): select(controllers)})
        )

    async def async_step_binding(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        assert self.resource_id is not None
        entry = self._get_entry()
        errors = {}
        device = getattr(entry.runtime_data, "control_devices", {}).get(self.resource_id, {})
        old = {"controller_kind": device.get("kind", "tap_dial")}
        if user_input is None and old.get("controller_kind") == "motion":
            try:
                old = await self.prepare_motion(old, self.resource_id)
            except BridgeError:
                errors["base"] = "motion_bridge_error"
        if user_input is not None:
            binding, error = controller_form(
                {**user_input, "controller_kind": old.get("controller_kind", "tap_dial")}
            )
            if not error:
                try:
                    await self.save_motion(binding, self.resource_id)
                except BridgeError:
                    error = "motion_bridge_error"
            if error:
                errors["base"] = error
                old = {**old, **binding}
                if old.get("controller_kind") == "motion":
                    old = self.motion_metadata(old, self.resource_id)
            else:
                return self.async_create_entry(
                    title=entry.runtime_data.controllers().get(self.resource_id, self.resource_id),
                    unique_id=self.resource_id,
                    data={
                        CONF_RESOURCE: self.resource_id,
                        "controller_model": device.get("model"),
                        **binding,
                    },
                )
        return self.async_show_form(
            step_id="binding"
            + (
                "_" + old["controller_kind"]
                if old.get("controller_kind", "tap_dial") != "tap_dial"
                else ""
            ),
            data_schema=binding_schema(old, user_input if errors else None),
            errors=errors,
            description_placeholders=self.motion_context(old, self.resource_id),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        old = dict(subentry.data)
        errors = {}
        if user_input is None and old.get("controller_kind") == "motion":
            try:
                old = await self.prepare_motion(old, subentry.data[CONF_RESOURCE])
            except BridgeError:
                errors["base"] = "motion_bridge_error"
        if user_input is not None:
            binding, error = controller_form(
                {**user_input, "controller_kind": old.get("controller_kind", "tap_dial")}
            )
            if not error:
                try:
                    await self.save_motion(binding, subentry.data[CONF_RESOURCE])
                except BridgeError:
                    error = "motion_bridge_error"
            if error:
                errors["base"] = error
                old = self.motion_metadata({**old, **binding}, subentry.data[CONF_RESOURCE])
            else:
                # Replace the binding so cleared optional buttons stay cleared.
                # The live runtime reads the updated binding without dropping timers.
                result = self.async_update_and_abort(
                    entry,
                    subentry,
                    data={
                        CONF_RESOURCE: subentry.data[CONF_RESOURCE],
                        "controller_model": old.get("controller_model"),
                        **binding,
                    },
                )
                if binding.get("controller_kind") == "motion":
                    await entry.runtime_data.reconfigure_motion(subentry.data[CONF_RESOURCE])
                return result

        return self.async_show_form(
            step_id="reconfigure"
            + (
                "_" + old["controller_kind"]
                if old.get("controller_kind", "tap_dial") != "tap_dial"
                else ""
            ),
            data_schema=binding_schema(old, user_input if errors else None),
            errors=errors,
            description_placeholders={
                "controller": subentry.title,
                **self.motion_context(old, subentry.data[CONF_RESOURCE]),
            },
        )

    async def async_step_binding_button(self, user_input=None):
        return await self.async_step_binding(user_input)

    async def async_step_binding_dimmer(self, user_input=None):
        return await self.async_step_binding(user_input)

    async def async_step_reconfigure_button(self, user_input=None):
        return await self.async_step_reconfigure(user_input)

    async def async_step_reconfigure_dimmer(self, user_input=None):
        return await self.async_step_reconfigure(user_input)

    async def async_step_binding_motion(self, user_input=None):
        return await self.async_step_binding(user_input)

    async def async_step_reconfigure_motion(self, user_input=None):
        return await self.async_step_reconfigure(user_input)
