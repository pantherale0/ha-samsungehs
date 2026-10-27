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
    DhwReferenceTemp,
    InFsv3042DayOfWeek,
    InUseThermostat,
    SamsungEnum,
)
from pysamsungnasa.protocol.enum import (
    InFsv2041WaterLawTypeHeating as InFsv2041WaterLawTypeHeatingEnum,
)
from pysamsungnasa.protocol.enum import (
    InFsv2093 as InFsv2093Enum,
)
from pysamsungnasa.protocol.enum import (
    InFsv4051 as InFsv4051Enum,
)
from pysamsungnasa.protocol.enum import (
    InFsv4053 as InFsv4053Enum,
)
from pysamsungnasa.protocol.factory.messages.indoor import (
    DhwReferenceTemperatureMessage,
    InFsv2041WaterLawTypeHeating,
    InFsv2091UseThermostat1,
    InFsv2092UseThermostat2,
    InFsv2093,
    InFsv3042,
    InFsv4051,
    InFsv4053,
)

from .entity import SamsungEhsEntity
from .helpers import convert_enum_to_select_options

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from pysamsungnasa.protocol.factory.types import BaseMessage

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEHSSelectKey(StrEnum):
    """Samsung EHS Select Keys."""

    TEMPERATURE_REFERENCE = "temperature_reference"
    USE_THERMOSTAT_ZONE_1 = "use_thermostat_zone_1"
    USE_THERMOSTAT_ZONE_2 = "use_thermostat_zone_2"
    WATER_LAW_TYPE_HEATING = "water_law_type_heating"
    REMOTE_CONTROLLER_ROOM_TEMP_CONTROL = "remote_controller_room_temp_control"
    DHW_DISINFECTION_DAY_OF_WEEK = "dhw_disinfection_day_of_week"
    PWM_PUMP_MODE = "pwm_pump_mode"
    INVERTER_PUMP_CONTROL_FACTOR = "inverter_pump_control_factor"
    DHW_SUPPLY_RATIO = "dhw_supply_ratio"


@dataclass(frozen=True, kw_only=True)
class SamsungEHSSelectEntityDescription(SelectEntityDescription):
    """Describes Samsung EHS select entity."""

    message: type[BaseMessage]
    options: type[SamsungEnum]
    requires_read: bool = False


SELECTS: tuple[SamsungEHSSelectEntityDescription, ...] = (
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.TEMPERATURE_REFERENCE,
        translation_key=SamsungEHSSelectKey.TEMPERATURE_REFERENCE,
        message=DhwReferenceTemperatureMessage,
        options=DhwReferenceTemp,
        requires_read=True,
    ),
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.WATER_LAW_TYPE_HEATING,
        translation_key=SamsungEHSSelectKey.WATER_LAW_TYPE_HEATING,
        message=InFsv2041WaterLawTypeHeating,
        options=InFsv2041WaterLawTypeHeatingEnum,
    ),
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.USE_THERMOSTAT_ZONE_1,
        translation_key=SamsungEHSSelectKey.USE_THERMOSTAT_ZONE_1,
        message=InFsv2091UseThermostat1,
        options=InUseThermostat,
    ),
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.USE_THERMOSTAT_ZONE_2,
        translation_key=SamsungEHSSelectKey.USE_THERMOSTAT_ZONE_2,
        message=InFsv2092UseThermostat2,
        options=InUseThermostat,
    ),
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.REMOTE_CONTROLLER_ROOM_TEMP_CONTROL,
        translation_key=SamsungEHSSelectKey.REMOTE_CONTROLLER_ROOM_TEMP_CONTROL,
        message=InFsv2093,
        options=InFsv2093Enum,
    ),
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
    SamsungEHSSelectEntityDescription(
        key=SamsungEHSSelectKey.INVERTER_PUMP_CONTROL_FACTOR,
        translation_key=SamsungEHSSelectKey.INVERTER_PUMP_CONTROL_FACTOR,
        message=InFsv4053,
        options=InFsv4053Enum,
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
        if (
            self._message is None
            or self._message.MESSAGE_ID not in self._device.attributes
        ):
            return None
        value = self._device.attributes[self._message.MESSAGE_ID].VALUE
        if value is None:
            return None
        enum_class = self.entity_description.options
        try:
            member = enum_class(value)
        except ValueError:
            return None
        return member.name.replace("_", " ").lower()

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return convert_enum_to_select_options(self.entity_description.options)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        for member in self.entity_description.options:
            if member.name.replace("_", " ").lower() == option.lower():
                await self._device.write_attribute(self._message, value=member)
                return
