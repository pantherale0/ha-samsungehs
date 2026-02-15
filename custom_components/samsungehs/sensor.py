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
from pysamsungnasa.protocol.factory.messages import basic, indoor, outdoor

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from pysamsungnasa.device import NasaDevice
    from pysamsungnasa.protocol.factory.types import BaseMessage

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEhsSensorKey(StrEnum):
    """Samsung EHS Sensor Keys."""

    # All devices
    LAST_PACKET_RECEIVED = "last_packet_received"
    AVAILABLE_ATTRIBUTES = "available_attributes"
    ERROR_CODE = "error_code"

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
    message: type[BaseMessage] | None = None
    value_fn: Callable[[NasaDevice], Any] | None = None


ALL_ENTITY_DESCRIPTIONS: tuple[SamsungEhsSensorEntityDescription, ...] = (
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.AVAILABLE_ATTRIBUTES,
        translation_key=SamsungEhsSensorKey.AVAILABLE_ATTRIBUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: len(device.attributes),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.ERROR_CODE,
        translation_key=SamsungEhsSensorKey.ERROR_CODE,
        entity_category=EntityCategory.DIAGNOSTIC,
        message=basic.CurrentErrorCode,
    ),
)

OUTDOOR_ENTITY_DESCRIPTIONS: tuple[SamsungEhsSensorEntityDescription, ...] = (
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.OUTDOOR_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.OUTDOOR_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        message=outdoor.OutdoorAirTemperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.OUTDOOR_COP,
        translation_key=SamsungEhsSensorKey.OUTDOOR_COP,
        value_fn=lambda device: (
            (
                indoor.TotalEnergyGenerated.MESSAGE_ID in device.attributes
                and outdoor.OutdoorCumulativeEnergy.MESSAGE_ID in device.attributes
                and (
                    consumption := device.attributes[
                        outdoor.OutdoorCumulativeEnergy.MESSAGE_ID
                    ].VALUE
                )
                != 0
                and (
                    generation := device.attributes[
                        indoor.TotalEnergyGenerated.MESSAGE_ID
                    ].VALUE
                )
                is not None
                and generation / consumption
            )
            or None
        ),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.POWER_GENERATION,
        translation_key=SamsungEhsSensorKey.POWER_GENERATION,
        message=indoor.InGeneratedPowerLastMinute,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.ENERGY_CONSUMPTION,
        translation_key=SamsungEhsSensorKey.ENERGY_CONSUMPTION,
        message=outdoor.OutdoorCumulativeEnergy,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.ENERGY_GENERATION,
        translation_key=SamsungEhsSensorKey.ENERGY_GENERATION,
        message=indoor.TotalEnergyGenerated,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.POWER_USAGE,
        translation_key=SamsungEhsSensorKey.POWER_USAGE,
        message=outdoor.OutdoorInstantaneousPower,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # SamsungEhsSensorEntityDescription(
    #     key=SamsungEhsSensorKey.WATER_PRESSURE,
    #     translation_key=SamsungEhsSensorKey.WATER_PRESSURE,
    #     native_unit_of_measurement="bar",
    #     device_class=SensorDeviceClass.PRESSURE,
    #     state_class=SensorStateClass.MEASUREMENT,
    #     message=0x82FE,
    # ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.COMPRESSOR_FREQUENCY,
        translation_key=SamsungEhsSensorKey.COMPRESSOR_FREQUENCY,
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorCompressorRunFrequency,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.TARGET_COMPRESSOR_FREQUENCY,
        translation_key=SamsungEhsSensorKey.TARGET_COMPRESSOR_FREQUENCY,
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorCompressorTargetFrequency,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.EVA_OUT_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.EVA_OUT_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorCombinedSuctionTemp,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.EVA_IN_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.EVA_IN_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorCondoutTemp,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.CONDENSER_OUT_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.CONDENSER_OUT_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.CondenserOutTemperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.CONDENSER_IN_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.CONDENSER_IN_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.CondenserInTemperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FAN_1_SPEED,
        translation_key=SamsungEhsSensorKey.FAN_1_SPEED,
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorFanRpm1,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FAN_2_SPEED,
        translation_key=SamsungEhsSensorKey.FAN_2_SPEED,
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorFanRpm2,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.EEV_POSITION,
        translation_key=SamsungEhsSensorKey.EEV_POSITION,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorEev1Opening,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.TW1_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.TW1_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorTw1Temperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.TW2_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.TW2_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorTw2Temperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.SUCTION_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.SUCTION_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorSuctionSensorTemperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.DISCHARGE_TARGET_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.DISCHARGE_TARGET_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=outdoor.OutdoorTargetDischargeTemperature,
    ),
)

INDOOR_ENTITY_DESCRIPTIONS: tuple[SamsungEhsSensorEntityDescription, ...] = (
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.WATER_PUMP_SPEED,
        translation_key=SamsungEhsSensorKey.WATER_PUMP_SPEED,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InWaterPumpPwmValueMessage,
        requires_read=True,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.RETURN_WATER_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.RETURN_WATER_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InTempWaterInMessage,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.LEAVING_WATER_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.LEAVING_WATER_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.IndoorFlowTemperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FLOW_RATE,
        translation_key=SamsungEhsSensorKey.FLOW_RATE,
        native_unit_of_measurement="L/min",
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InFlowSensorCalculationMessage,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.FLOW_SETPOINT_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.FLOW_SETPOINT_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InWaterOutletTargetTemperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.WATER_LAW_TARGET_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.WATER_LAW_TARGET_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InWaterLawTargetTemperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.COMPRESSOR_DHW_STANDARD_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.COMPRESSOR_DHW_STANDARD_TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InFsv5021,
        requires_read=True,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.DHW_MIN_OPERATING_TIME,
        translation_key=SamsungEhsSensorKey.DHW_MIN_OPERATING_TIME,
        native_unit_of_measurement="minutes",
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InFsv3024,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.DHW_MAX_OPERATING_TIME,
        translation_key=SamsungEhsSensorKey.DHW_MAX_OPERATING_TIME,
        native_unit_of_measurement="minutes",
        state_class=SensorStateClass.MEASUREMENT,
        message=indoor.InFsv3025,
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
            message=entity_description.message,
            key=entity_description.key,
            requires_read=entity_description.requires_read,
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> int | float | None:
        """Return the native value."""
        if self._device is None:
            return None
        if self.entity_description.message is not None:
            if self.entity_description.message.MESSAGE_ID in self._device.attributes:
                val = self._device.attributes[
                    self.entity_description.message.MESSAGE_ID
                ].VALUE
                if val == "ffff":  # Sensor not available for this device
                    return None
                return val
            return None
        if self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self._device)

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        if self._device is None:
            return False
        if (
            self.entity_description.value_fn is None
            and self.entity_description.message is None
        ):
            return False
        if self.entity_description.message is None:
            return True
        return (
            self.coordinator.config_entry.runtime_data.client.client.is_connected
            and self.entity_description.message.MESSAGE_ID in self._device.attributes
            and self._device.attributes[
                self.entity_description.message.MESSAGE_ID
            ].VALUE
            != "ffff"
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
                "value": str(value.VALUE),
            }
            for msg_number, value in self._device.attributes.items()
        }

    async def async_added_to_hass(self) -> None:
        """Execute when entity is added to hass."""
        # We need to subscribe to updates for two messages
        # These are added because they are part of a different type of NASA device
        if self.entity_description.message is None:
            return await super().async_added_to_hass()
        if (
            self.entity_description.message.MESSAGE_ID in (0x4426, 0x4427)
            and self._device.device_type == AddressClass.OUTDOOR
        ):
            self.coordinator.config_entry.runtime_data.client.parser.add_packet_listener(
                0x4426, self._device.handle_packet
            )
            self.coordinator.config_entry.runtime_data.client.parser.add_packet_listener(
                0x4427, self._device.handle_packet
            )
        return await super().async_added_to_hass()
