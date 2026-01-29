# pylint: disable=E1123
"""Number platform for Samsung EHS integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import PERCENTAGE, UnitOfTime, UnitOfTemperature
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import (
    AddressClass,
)
from pysamsungnasa.protocol.factory.messages.indoor import (
    InFsv2021WaterOutTempWL1HeatingMax,
    InFsv2022WaterOutTempWL1HeatingMin,
    InFsv3025,
    InFsv3043,
    InFsv3044,
    InFsv3045,
    InFsv3046,
    InFsv5051,
    InOutdoorCompressorFrequencyRateControlMessage,
)

from .entity import SamsungEhsEntity
from .helpers import get_dict_value

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from pysamsungnasa.device import NasaDevice
    from pysamsungnasa.protocol.factory.types import BaseMessage

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEHSNumberKey(StrEnum):
    """Samsung EHS Number Keys."""

    FREQUENCY_RATIO_CONTROL_PERCENT = "frequency_ratio_control_percent"
    DHW_DISINFECTION_START_HOUR = "dhw_disinfection_start_hour"
    DHW_DISINFECTION_TARGET_TEMPERATURE = "dhw_disinfection_target_temperature"
    DHW_DISINFECTION_DURATION_MINUTES = "dhw_disinfection_duration_minutes"
    DHW_DISINFECTION_MAX_HOURS = "dhw_disinfection_max_hours"
    DHW_MAX_OPERATION_TIME = "dhw_max_operation_time"
    FSV2021_WATER_OUT_TEMP_WL1_HEATING_MAX = "fsv2021_water_out_temp_wl1_heating_max"
    FSV2022_WATER_OUT_TEMP_WL1_HEATING_MIN = "fsv2022_water_out_temp_wl1_heating_min"


@dataclass(frozen=True, kw_only=True)
class SamsungEHSNumberEntityDescription(NumberEntityDescription):
    """Describes Samsung EHS number entity."""

    message: type[BaseMessage] | None = None
    write_fn: (
        Callable[[NasaDevice, float], Coroutine[NasaDevice, float, None]] | None
    ) = None
    available_fn: Callable[[SamsungEhsEntity], bool] | None = None
    value_fn: Callable[[NasaDevice], float | None] | None = None
    requires_read: bool = False


NUMBERS: tuple[SamsungEHSNumberEntityDescription, ...] = (
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.FREQUENCY_RATIO_CONTROL_PERCENT,
        message=InOutdoorCompressorFrequencyRateControlMessage,
        write_fn=lambda device, value: device.write_attribute(
            InOutdoorCompressorFrequencyRateControlMessage,
            value={"frequency_ratio_percent": int(value)},
        ),
        value_fn=lambda device: get_dict_value(
            device.attributes[
                InOutdoorCompressorFrequencyRateControlMessage.MESSAGE_ID
            ],
            "frequency_ratio_percent",
        )
        if InOutdoorCompressorFrequencyRateControlMessage.MESSAGE_ID is not None
        else None,
        translation_key=SamsungEHSNumberKey.FREQUENCY_RATIO_CONTROL_PERCENT,
        requires_read=True,
        native_step=10.0,
        native_min_value=50.0,
        native_max_value=150.0,
        native_unit_of_measurement=PERCENTAGE,
        available_fn=lambda entity: entity.get_attribute(InFsv5051) is not None
        and bool(entity.get_attribute(InFsv5051)),
    ),
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.DHW_DISINFECTION_START_HOUR,
        message=InFsv3043,
        write_fn=lambda device, value: device.write_attribute(
            InFsv3043,
            value=int(value),
        ),
        translation_key=SamsungEHSNumberKey.DHW_DISINFECTION_START_HOUR,
        requires_read=True,
        native_step=1.0,
        native_min_value=0.0,
        native_max_value=23.0,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.DHW_DISINFECTION_TARGET_TEMPERATURE,
        message=InFsv3044,
        write_fn=lambda device, value: device.write_attribute(
            InFsv3044,
            value=int(value),
        ),
        translation_key=SamsungEHSNumberKey.DHW_DISINFECTION_TARGET_TEMPERATURE,
        requires_read=True,
        native_step=1.0,
        native_min_value=40.0,
        native_max_value=70.0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.DHW_DISINFECTION_DURATION_MINUTES,
        message=InFsv3045,
        write_fn=lambda device, value: device.write_attribute(
            InFsv3045,
            value=int(value),
        ),
        translation_key=SamsungEHSNumberKey.DHW_DISINFECTION_DURATION_MINUTES,
        requires_read=True,
        native_step=1.0,
        native_min_value=5.0,
        native_max_value=60.0,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.DHW_DISINFECTION_MAX_HOURS,
        message=InFsv3046,
        write_fn=lambda device, value: device.write_attribute(
            InFsv3046,
            value=int(value),
        ),
        translation_key=SamsungEHSNumberKey.DHW_DISINFECTION_MAX_HOURS,
        requires_read=True,
        native_step=1.0,
        native_min_value=1.0,
        native_max_value=24.0,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.DHW_MAX_OPERATION_TIME,
        message=InFsv3025,
        write_fn=lambda device, value: device.write_attribute(
            InFsv3025,
            value=value,
        ),
        translation_key=SamsungEHSNumberKey.DHW_MAX_OPERATION_TIME,
        requires_read=True,
        native_step=0.1,
        native_min_value=5.0,
        native_max_value=95.0,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.FSV2021_WATER_OUT_TEMP_WL1_HEATING_MAX,
        message=InFsv2021WaterOutTempWL1HeatingMax,
        write_fn=lambda device, value: device.write_attribute(
            InFsv2021WaterOutTempWL1HeatingMax,
            value=value,
        ),
        translation_key=SamsungEHSNumberKey.FSV2021_WATER_OUT_TEMP_WL1_HEATING_MAX,
        requires_read=True,
        native_step=0.1,
        native_min_value=17.0,
        native_max_value=65.0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SamsungEHSNumberEntityDescription(
        key=SamsungEHSNumberKey.FSV2022_WATER_OUT_TEMP_WL1_HEATING_MIN,
        message=InFsv2022WaterOutTempWL1HeatingMin,
        write_fn=lambda device, value: device.write_attribute(
            InFsv2022WaterOutTempWL1HeatingMin,
            value=int(value),
        ),
        translation_key=SamsungEHSNumberKey.FSV2022_WATER_OUT_TEMP_WL1_HEATING_MIN,
        requires_read=True,
        native_step=1.0,
        native_min_value=17.0,
        native_max_value=65.0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung EHS number based on a config entry."""
    for subentry in entry.subentries.values():
        if not subentry.unique_id:
            continue
        if Address.parse(subentry.unique_id).class_id != AddressClass.INDOOR:
            continue
        async_add_entities(
            [
                SamsungEHSNumber(entry.runtime_data.coordinator, description, subentry)
                for description in NUMBERS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class SamsungEHSNumber(SamsungEhsEntity, NumberEntity):
    """Representation of a Samsung EHS number."""

    entity_description: SamsungEHSNumberEntityDescription

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        description: SamsungEHSNumberEntityDescription,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the number."""
        super().__init__(
            coordinator,
            message=description.message,
            key=description.key,
            requires_read=description.requires_read,
            subentry=subentry,
        )
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        if self.entity_description.available_fn is not None:
            return super().available and self.entity_description.available_fn(self)
        return super().available

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self._device is None:
            return None
        if (
            self._message is None
            or self._message.MESSAGE_ID not in self._device.attributes
        ):
            return None
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(self._device)
        value = self._device.attributes[self._message.MESSAGE_ID].VALUE
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the native value."""
        if self._message is None:
            return
        if self.entity_description.write_fn is not None:
            await self.entity_description.write_fn(self._device, value)
        else:
            await self._device.write_attribute(self._message, value=value)
