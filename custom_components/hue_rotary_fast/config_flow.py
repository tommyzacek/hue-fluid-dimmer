"""Select an existing Hue bridge and configure all its controllers in the GUI."""

from typing import Any

import probatio as p
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BINDINGS,
    CONF_HUE_ENTRY,
    CONF_INTERVAL,
    CONF_MODE,
    CONF_WINDOW,
    DEFAULT_INTERVAL,
    DEFAULT_WINDOW,
    DOMAIN,
    HUE_DOMAIN,
    MODE_ACTIVE,
    MODE_CONTINUOUS,
)


def select(options: dict[str, str]) -> selector.SelectSelector:
    return selector.SelectSelector(
        {"options": [{"value": value, "label": label} for value, label in options.items()]}
    )


def number(minimum: float, maximum: float, step: float) -> selector.NumberSelector:
    return selector.NumberSelector({"min": minimum, "max": maximum, "step": step, "mode": "box"})


class HueRotaryFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HueRotaryOptionsFlow()

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
                title=f"Hue Rotary Fast – {bridges[entry_id]}", data={CONF_HUE_ENTRY: entry_id}
            )
        return self.async_show_form(
            step_id="user", data_schema=p.Schema({p.Required(CONF_HUE_ENTRY): select(bridges)})
        )


class HueRotaryOptionsFlow(OptionsFlow):
    resource_id: str | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["polling", "controller"])

    async def async_step_polling(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self.config_entry.options, **user_input}
            )
        options = self.config_entry.options
        return self.async_show_form(
            step_id="polling",
            data_schema=p.Schema(
                {
                    p.Required(CONF_MODE, default=options.get(CONF_MODE, MODE_ACTIVE)): select(
                        {
                            MODE_ACTIVE: "Only during rotation / Jen při otáčení",
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

    async def async_step_controller(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        controllers = self.config_entry.runtime_data.controllers()
        if not controllers:
            return self.async_abort(reason="no_controllers")
        if user_input is not None:
            self.resource_id = user_input["controller"]
            if self.resource_id not in controllers:
                return self.async_abort(reason="no_controllers")
            return await self.async_step_binding()
        return self.async_show_form(
            step_id="controller",
            data_schema=p.Schema({p.Required("controller"): select(controllers)}),
        )

    async def async_step_binding(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self.resource_id is not None
        bindings = dict(self.config_entry.options.get(CONF_BINDINGS, {}))
        old = bindings.get(self.resource_id, {})
        errors = {}
        if user_input is not None:
            if user_input.get("enabled") and not user_input.get("lights"):
                errors["lights"] = "lights_required"
                old = user_input
            else:
                # Absent optional button fields remove an earlier assignment.
                bindings[self.resource_id] = user_input
                return self.async_create_entry(
                    title="", data={**self.config_entry.options, CONF_BINDINGS: bindings}
                )
        schema = {
            p.Required("enabled", default=old.get("enabled", False)): bool,
            p.Optional("lights", default=old.get("lights", [])): selector.EntitySelector(
                {"domain": "light", "multiple": True}
            ),
            p.Required("sensitivity", default=old.get("sensitivity", 1.5)): number(0.1, 10, 0.1),
            p.Required("transition", default=old.get("transition", 1)): number(0.1, 3, 0.1),
        }
        for index in range(1, 5):
            field = f"button_{index}"
            key = p.Optional(field, default=old[field]) if old.get(field) else p.Optional(field)
            schema[key] = selector.EntitySelector({"domain": ["scene", "script", "light"]})
        return self.async_show_form(step_id="binding", data_schema=p.Schema(schema), errors=errors)
