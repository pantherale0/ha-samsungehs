# pylint: disable=E1123
"""Sensor platform for samsungehs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import AddressClass

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from pysamsungnasa.device import IndoorNasaDevice, NasaDevice, OutdoorNasaDevice

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEhsSensorKey(StrEnum):
    """Samsung EHS Sensor Keys."""

    # All devices
    LAST_PACKET_RECEIVED = "last_packet_received"
    AVAILABLE_ATTRIBUTES = "available_attributes"

    # Outdoor unit only
    OUTDOOR_TEMPERATURE = "outdoor_temperature"
    OUTDOOR_COP = "outdoor_cop"
    POWER_GENERATION = "power_generation"
    ENERGY_CONSUMPTION = "energy_consumption"
    ENERGY_GENERATION = "energy_generation"
    POWER_USAGE = "power_usage"
    WATER_PRESSURE = "water_pressure"
    COMPRESSOR_FREQUENCY = "compressor_frequency"
    TARGET_COMPRESSOR_FREQUENCY = "target_compressor_frequency"
    EVA_OUT_TEMPERATURE = "eva_out_temperature"
    EVA_IN_TEMPERATURE = "eva_in_temperature"
    CONDENSER_OUT_TEMPERATURE = "condenser_out_temperature"
    CONDENSER_IN_TEMPERATURE = "condenser_in_temperature"
    FAN_1_SPEED = "fan_1_speed"
    FAN_2_SPEED = "fan_2_speed"
    EEV_POSITION = "eev_position"
    TW1_TEMPERATURE = "tw1_temperature"
    TW2_TEMPERATURE = "tw2_temperature"
    SUCTION_TEMPERATURE = "suction_temperature"
    DISCHARGE_TARGET_TEMPERATURE = "discharge_target_temperature"

    # Indoor unit only
    WATER_PUMP_SPEED = "water_pump_speed"
    LEAVING_WATER_TEMPERATURE = "leaving_water_temperature"
    RETURN_WATER_TEMPERATURE = "return_water_temperature"
    FLOW_RATE = "flow_rate"
    FLOW_SETPOINT_TEMPERATURE = "flow_set_point_temperature"
    WATER_LAW_TARGET_TEMPERATURE = "water_law_target_temperature"
    COMPRESSOR_DHW_STANDARD_TEMPERATURE = "compressor_dhw_standard_temperature"
    DHW_MIN_OPERATING_TIME = "dhw_min_operating_time"
    DHW_MAX_OPERATING_TIME = "dhw_max_operating_time"


@dataclass(kw_only=True, frozen=True)
class SamsungEhsSensorEntityDescription(SensorEntityDescription):
    """Description for Samsung EHS sensor entities."""

    requires_read: bool = (
        False  # If true the sensor requires a read command to retrieve
    )
    message_number: int | None = None
    value_fn: Callable[[OutdoorNasaDevice | IndoorNasaDevice | NasaDevice], Any]


@dataclass(kw_only=True, frozen=True)
class IndoorEhsSensorEntityDescription(SamsungEhsSensorEntityDescription):
    """Description for Samsung EHS sensor entities."""

    value_fn: Callable[[IndoorNasaDevice], Any] | None = None


@dataclass(kw_only=True, frozen=True)
class OutdoorEhsSensorEntityDescription(SamsungEhsSensorEntityDescription):
    """Description for Samsung EHS sensor entities."""

    value_fn: Callable[[OutdoorNasaDevice], Any] | None = None


ALL_ENTITY_DESCRIPTIONS: tuple[SamsungEhsSensorEntityDescription, ...] = (
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.AVAILABLE_ATTRIBUTES,
        translation_key=SamsungEhsSensorKey.AVAILABLE_ATTRIBUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: len(device.attributes),
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

OUTDOOR_ENTITY_DESCRIPTIONS: tuple[OutdoorEhsSensorEntityDescription, ...] = (
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.OUTDOOR_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.OUTDOOR_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: device.outdoor_temperature,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.OUTDOOR_COP,
        translation_key=SamsungEhsSensorKey.OUTDOOR_COP,
        value_fn=lambda device: device.cop_rating,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.POWER_GENERATION,
        translation_key=SamsungEhsSensorKey.POWER_GENERATION,
        value_fn=lambda device: device.power_generated_last_minute,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.ENERGY_CONSUMPTION,
        translation_key=SamsungEhsSensorKey.ENERGY_CONSUMPTION,
        value_fn=lambda device: device.cumulative_energy,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.ENERGY_GENERATION,
        translation_key=SamsungEhsSensorKey.ENERGY_GENERATION,
        value_fn=lambda device: device.power_produced,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.POWER_USAGE,
        translation_key=SamsungEhsSensorKey.POWER_USAGE,
        value_fn=lambda device: device.power_consumption,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.WATER_PRESSURE,
        translation_key=SamsungEhsSensorKey.WATER_PRESSURE,
        native_unit_of_measurement="bar",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x82FE,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.COMPRESSOR_FREQUENCY,
        translation_key=SamsungEhsSensorKey.COMPRESSOR_FREQUENCY,
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x8238,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.TARGET_COMPRESSOR_FREQUENCY,
        translation_key=SamsungEhsSensorKey.TARGET_COMPRESSOR_FREQUENCY,
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x8237,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.EVA_OUT_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.EVA_OUT_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x82E7,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.EVA_IN_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.EVA_IN_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x8218,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.CONDENSER_OUT_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.CONDENSER_OUT_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x82DE,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.CONDENSER_IN_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.CONDENSER_IN_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x820A,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FAN_1_SPEED,
        translation_key=SamsungEhsSensorKey.FAN_1_SPEED,
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x823D,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FAN_2_SPEED,
        translation_key=SamsungEhsSensorKey.FAN_2_SPEED,
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x823E,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.EEV_POSITION,
        translation_key=SamsungEhsSensorKey.EEV_POSITION,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x8229,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.TW1_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.TW1_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x82DF,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.TW2_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.TW2_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x82E0,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.SUCTION_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.SUCTION_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x821A,
    ),
    OutdoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.DISCHARGE_TARGET_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.DISCHARGE_TARGET_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x8223,
    ),
)

INDOOR_ENTITY_DESCRIPTIONS: tuple[IndoorEhsSensorEntityDescription, ...] = (
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.WATER_PUMP_SPEED,
        translation_key=SamsungEhsSensorKey.WATER_PUMP_SPEED,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x40C4,
        requires_read=True,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.RETURN_WATER_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.RETURN_WATER_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x4236,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.LEAVING_WATER_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.LEAVING_WATER_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x4238,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FLOW_RATE,
        translation_key=SamsungEhsSensorKey.FLOW_RATE,
        native_unit_of_measurement="L/min",
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x42E9,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FLOW_SETPOINT_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.FLOW_SETPOINT_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x4247,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.WATER_LAW_TARGET_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.WATER_LAW_TARGET_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x4248,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.COMPRESSOR_DHW_STANDARD_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.COMPRESSOR_DHW_STANDARD_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x427C,
        requires_read=True,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.DHW_MIN_OPERATING_TIME,
        translation_key=SamsungEhsSensorKey.DHW_MIN_OPERATING_TIME,
        native_unit_of_measurement="minutes",
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x4263,
    ),
    IndoorEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.DHW_MAX_OPERATING_TIME,
        translation_key=SamsungEhsSensorKey.DHW_MAX_OPERATING_TIME,
        native_unit_of_measurement="minutes",
        state_class=SensorStateClass.MEASUREMENT,
        message_number=0x4264,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # pylint: disable=W0613
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Register devices in the device registry
    for subentry in entry.subentries.values():
        assert subentry.unique_id is not None  # noqa: S101
        address = Address.parse(subentry.unique_id)
        async_add_entities(
            [
                SamsungEhsSensor(
                    coordinator=entry.runtime_data.coordinator,
                    subentry=subentry,
                    entity_description=entity_description,
                )
                for entity_description in ALL_ENTITY_DESCRIPTIONS
            ],
            config_subentry_id=subentry.subentry_id,
        )
        if address.class_id == AddressClass.OUTDOOR:
            async_add_entities(
                [
                    SamsungEhsSensor(
                        coordinator=entry.runtime_data.coordinator,
                        subentry=subentry,
                        entity_description=entity_description,
                    )
                    for entity_description in OUTDOOR_ENTITY_DESCRIPTIONS
                ],
                config_subentry_id=subentry.subentry_id,
            )
        elif address.class_id == AddressClass.INDOOR:
            async_add_entities(
                [
                    SamsungEhsSensor(
                        coordinator=entry.runtime_data.coordinator,
                        subentry=subentry,
                        entity_description=entity_description,
                    )
                    for entity_description in INDOOR_ENTITY_DESCRIPTIONS
                ],
                config_subentry_id=subentry.subentry_id,
            )


class SamsungEhsSensor(SamsungEhsEntity, SensorEntity):
    """samsungehs Sensor class."""

    entity_description: SamsungEhsSensorEntityDescription

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        entity_description: SamsungEhsSensorEntityDescription,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(
            coordinator,
            subentry=subentry,
            message_number=entity_description.message_number,
            key=entity_description.key,
            requires_read=entity_description.requires_read,
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> int | float | None:
        """Return the native value."""
        if self._device is None:
            return None
        if self.entity_description.message_number is not None:
            if self.entity_description.message_number in self._device.attributes:
                val = self._device.attributes[
                    self.entity_description.message_number
                ].VALUE
                if val == "ffff":  # Sensor not available for this device
                    return None
                return val
            return None
        return self.entity_description.value_fn(self._device)

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        if self._device is None:
            return False
        if self.entity_description.value_fn is not None:
            return True
        return (
            self.coordinator.config_entry.runtime_data.client.client.is_connected
            and self._message_number in self._device.attributes
            and self._device.attributes[self._message_number].VALUE != "ffff"
        )

    @property
    def extra_state_attributes(self) -> dict[int, Any]:
        """Return extra state attributes."""
        if self.entity_description.key is not SamsungEhsSensorKey.AVAILABLE_ATTRIBUTES:
            return {}
        if self._device is None:
            return {}
        return {
            msg_number: {
                "name": value.MESSAGE_NAME,
                "value": value.VALUE,
            }
            for msg_number, value in self._device.attributes.items()
        }
