"""Native HA event entity for each rotary resource."""

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HueRotaryEntry
from .const import DOMAIN
from .models import Rotation


async def async_setup_entry(
    hass: HomeAssistant, entry: HueRotaryEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        [
            RotaryEvent(entry, resource)
            for resource in entry.runtime_data.resources
            if resource.get("id") and resource.get("owner", {}).get("rid")
        ]
    )


class RotaryEvent(EventEntity):
    _attr_has_entity_name = True
    _attr_name = "Fast rotation"
    _attr_should_poll = False
    _attr_event_types = ["start", "repeat"]

    def __init__(self, entry: HueRotaryEntry, resource: dict) -> None:
        self.runtime = entry.runtime_data
        self.resource_id = resource["id"]
        self._attr_unique_id = resource["id"]
        # Keep our registry ownership separate from the official Hue integration.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, resource["owner"]["rid"])},
            name=self.runtime.controllers()[resource["id"]],
            manufacturer="Signify",
            model="Hue rotary controller",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.runtime.subscribe(self.resource_id, self.handle_rotation))

    @callback
    def handle_rotation(self, report: Rotation) -> None:
        self._trigger_event(report.action, report.event_data())
        self.async_write_ha_state()
