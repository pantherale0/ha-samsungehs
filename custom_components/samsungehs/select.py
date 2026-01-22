# pylint: disable=E1123
"""Select platform for Samsung EHS integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import (
    AddressClass,
    InFsv3042DayOfWeek,
    SamsungEnum,
)
from pysamsungnasa.protocol.enum import (
    InFsv4051 as InFsv4051Enum,
)
from pysamsungnasa.protocol.factory.messages.indoor import (
    InFsv3042,
    InFsv4051,
)
from pysamsungnasa.protocol.factory.types import BaseMessage

from .entity import SamsungEhsEntity
from .helpers import convert_enum_to_select_options

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEHSSelectKey(StrEnum):
    """Samsung EHS Select Keys."""

    DHW_DISINFECTION_DAY_OF_WEEK = "dhw_disinfection_day_of_week"
    PWM_PUMP_MODE = "pwm_pump_mode"
    DHW_SUPPLY_RATIO = "dhw_supply_ratio"


@dataclass(frozen=True, kw_only=True)
class SamsungEHSSelectEntityDescription(SelectEntityDescription):
    """Describes Samsung EHS select entity."""

    message: type[BaseMessage]
    options: type[SamsungEnum] | None = None
    requires_read: bool = False


SELECTS: tuple[SamsungEHSSelectEntityDescription, ...] = (
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.DHW_DISINFECTION_DAY_OF_WEEK,
        translation_key=SamsungEHSSelectKey.DHW_DISINFECTION_DAY_OF_WEEK,
        message=InFsv3042,
        options=InFsv3042DayOfWeek,
    ),
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.PWM_PUMP_MODE,
        translation_key=SamsungEHSSelectKey.PWM_PUMP_MODE,
        message=InFsv4051,
        options=InFsv4051Enum,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung EHS select based on a config entry."""
    for subentry in entry.subentries.values():
        if not subentry.unique_id:
            continue
        if Address.parse(subentry.unique_id).class_id != AddressClass.INDOOR:
            continue
        async_add_entities(
            [
                SamsungEHSSelect(entry.runtime_data.coordinator, description, subentry)
                for description in SELECTS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class SamsungEHSSelect(SamsungEhsEntity, SelectEntity):
    """Representation of a Samsung EHS select."""

    entity_description: SamsungEHSSelectEntityDescription

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        description: SamsungEHSSelectEntityDescription,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the select."""
        super().__init__(
            coordinator,
            message=description.message,
            key=description.key,
            requires_read=description.requires_read,
            subentry=subentry,
        )
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        if self._device is None:
            return None
        if (
            self._message is None
            or self._message.MESSAGE_ID not in self._device.attributes
        ):
            return None
        value = self._device.attributes[self._message.MESSAGE_ID].VALUE
        if value is None:
            return None
        if self.options and isinstance(value, int) and 0 <= value < len(self.options):
            return self.options[value]
        return str(value)

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        if self.entity_description.options is not None:
            return convert_enum_to_select_options(self.entity_description.options)
        return []

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if self._message is None or self.entity_description.options is None:
            return
        try:
            value = self.options.index(option.lower())
            # Convert int to enum
            value = self.entity_description.options(value)
            await self._device.write_attribute(self._message, value=value)
        except ValueError:
            pass
