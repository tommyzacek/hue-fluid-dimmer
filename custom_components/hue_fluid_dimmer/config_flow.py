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


def select(options: dict[str, str]) -> selector.SelectSelector:
    return selector.SelectSelector(
        {"options": [{"value": value, "label": label} for value, label in options.items()]}
    )


def number(minimum: float, maximum: float, step: float) -> selector.NumberSelector:
    return selector.NumberSelector({"min": minimum, "max": maximum, "step": step, "mode": "box"})


class VisibleNumber(selector.NumberSelector):
    def serialize(self):
        return {**super().serialize(), "visible": {"field": "profile", "value": "custom"}}


class VisibleLights(selector.EntitySelector):
    def serialize(self):
        return {**super().serialize(), "visible": {"field": "source", "value": "custom"}}


class VisibleActionTargets(selector.EntitySelector):
    def __init__(self, action: str):
        super().__init__({"domain": ["light", "scene", "script"], "multiple": True})
        self.action = action

    def serialize(self):
        return {
            **super().serialize(),
            "visible": {"field": f"{self.action}_enabled", "value": True},
        }


def binding_schema(old: dict, submitted: dict | None = None) -> p.Schema:
    data = submitted if submitted is not None else form_values(old)
    dial = data["dial"]
    schema = {
        p.Required("enabled", default=data["enabled"]): bool,
        p.Required("dial", default=data["dial"]): section(
            p.Schema(
                {
                    p.Required("profile", default=dial["profile"]): selector.SelectSelector(
                        {
                            "options": ["gentle", "balanced", "swift", "custom"],
                            "translation_key": "dial_profile",
                            "mode": "list",
                        }
                    ),
                    p.Required("source", default=dial["source"]): selector.SelectSelector(
                        {
                            "options": ["button_1", "button_2", "button_3", "button_4", "custom"],
                            "translation_key": "dial_source",
                            "mode": "dropdown",
                        }
                    ),
                    p.Optional("lights", default=dial["lights"]): VisibleLights(
                        {"domain": "light", "multiple": True}
                    ),
                    p.Required("sensitivity", default=dial["sensitivity"]): VisibleNumber(
                        {"min": 0.1, "max": 10, "step": 0.05, "mode": "box"}
                    ),
                    p.Required("transition", default=dial["transition"]): VisibleNumber(
                        {"min": 0.1, "max": 3, "step": 0.1, "mode": "box"}
                    ),
                }
            )
        ),
    }
    for index in range(1, 5):
        field = f"button_{index}"
        fields = {}
        for action in GESTURES:
            fields[p.Required(f"{action}_enabled", default=data[field][f"{action}_enabled"])] = bool
            fields[p.Optional(f"{action}_targets", default=data[field][f"{action}_targets"])] = (
                VisibleActionTargets(action)
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
                title=f"Hue Fluid Dimmer – {bridges[entry_id]}", data={CONF_HUE_ENTRY: entry_id}
            )
        return self.async_show_form(
            step_id="user", data_schema=p.Schema({p.Required(CONF_HUE_ENTRY): select(bridges)})
        )


class HueFluidDimmerOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self.async_step_polling(user_input)

    async def async_step_polling(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self.config_entry.options, **user_input}
            )
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=p.Schema(
                {
                    p.Required(CONF_MODE, default=options.get(CONF_MODE, MODE_ACTIVE)): select(
                        {
                            MODE_ACTIVE: "After first event / Po první události",
                            MODE_CONTINUOUS: "Continuous / Trvale",
                        }
                    ),
                    p.Required(
                        CONF_INTERVAL, default=options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
                    ): number(0.1, 2, 0.05),
                    p.Required(
                        CONF_WINDOW, default=options.get(CONF_WINDOW, DEFAULT_WINDOW)
                    ): number(1, 10, 0.5),
                }
            ),
        )


class TapDialSubentryFlow(ConfigSubentryFlow):
    """Open a specific controller directly from its configuration row."""

    resource_id: str | None = None

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
        old = {}
        if user_input is not None:
            binding, error = parse_form(user_input)
            if error:
                errors["base"] = error
                old = binding
            else:
                return self.async_create_entry(
                    title=entry.runtime_data.controllers().get(self.resource_id, self.resource_id),
                    unique_id=self.resource_id,
                    data={CONF_RESOURCE: self.resource_id, **binding},
                )
        return self.async_show_form(
            step_id="binding",
            data_schema=binding_schema(old, user_input if errors else None),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        old = dict(subentry.data)
        errors = {}
        if user_input is not None:
            binding, error = parse_form(user_input)
            if error:
                errors["base"] = error
                old = binding
            else:
                # Replace the binding so cleared optional buttons stay cleared.
                # Updating the subentry invokes the parent's existing reload listener.
                return self.async_update_and_abort(
                    entry,
                    subentry,
                    data={CONF_RESOURCE: subentry.data[CONF_RESOURCE], **binding},
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=binding_schema(old, user_input if errors else None),
            errors=errors,
            description_placeholders={"controller": subentry.title},
        )
