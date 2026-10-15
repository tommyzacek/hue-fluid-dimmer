"""Brand changes preserve installation identity and user configuration."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.hue_fluid_dimmer.configuration import update_brand_title
from custom_components.hue_fluid_dimmer.const import DOMAIN


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Hue Fluid Dimmer – Kitchen", "Hue Reconfigo – Kitchen"),
        ("Hue Reconfigo – Kitchen", None),
        ("My lighting", None),
        ("Hue Fluid Dimmer custom name", None),
    ],
)
def test_rebrand_preserves_custom_titles_and_bindings(title, expected):
    entry = SimpleNamespace(title=title, data={"controllers": {"one": {"enabled": True}}})
    update = Mock()
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=update))
    update_brand_title(hass, entry)
    if expected is None:
        update.assert_not_called()
    else:
        update.assert_called_once_with(entry, title=expected)
    assert entry.data == {"controllers": {"one": {"enabled": True}}}
    assert DOMAIN == "hue_fluid_dimmer"
