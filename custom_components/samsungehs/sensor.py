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
    EntityCategory,
    UnitOfTemperature,
    UnitOfPower,
    UnitOfEnergy,
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

    LAST_PACKET_RECEIVED = "last_packet_received"
    AVAILABLE_ATTRIBUTES = "available_attributes"
    OUTDOOR_TEMPERATURE = "outdoor_temperature"
    OUTDOOR_COP = "outdoor_cop"
    POWER_GENERATION = "power_generation"
    ENERGY_CONSUMPTION = "energy_consumption"
    ENERGY_GENERATION = "energy_generation"
    POWER_USAGE = "power_usage"


@dataclass(kw_only=True, frozen=True)
class SamsungEhsSensorEntityDescription(SensorEntityDescription):
    """Description for Samsung EHS sensor entities."""

    message_number: int | None = None
    value_fn: Callable[[OutdoorNasaDevice | IndoorNasaDevice | NasaDevice], Any]


ALL_ENTITY_DESCRIPTIONS: tuple[SamsungEhsSensorEntityDescription, ...] = (
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.AVAILABLE_ATTRIBUTES,
        translation_key=SamsungEhsSensorKey.AVAILABLE_ATTRIBUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: len(device.attributes),
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

OUTDOOR_ENTITY_DESCRIPTIONS: tuple[SamsungEhsSensorEntityDescription, ...] = (
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.OUTDOOR_TEMPERATURE,
        translation_key=SamsungEhsSensorKey.OUTDOOR_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: device.outdoor_temperature,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.OUTDOOR_COP,
        translation_key=SamsungEhsSensorKey.OUTDOOR_COP,
        value_fn=lambda device: device.cop_rating,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.POWER_GENERATION,
        translation_key=SamsungEhsSensorKey.POWER_GENERATION,
        value_fn=lambda device: device.power_generated_last_minute,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.ENERGY_CONSUMPTION,
        translation_key=SamsungEhsSensorKey.ENERGY_CONSUMPTION,
        value_fn=lambda device: device.cumulative_energy,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.ENERGY_GENERATION,
        translation_key=SamsungEhsSensorKey.ENERGY_GENERATION,
        value_fn=lambda device: device.power_produced,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SamsungEhsSensorEntityDescription(
        key=SamsungEhsSensorKey.POWER_USAGE,
        translation_key=SamsungEhsSensorKey.POWER_USAGE,
        value_fn=lambda device: device.power_consumption,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
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
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> int | float | None:
        """Return the native value."""
        if self._device is None:
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
