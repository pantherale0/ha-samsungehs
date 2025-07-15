"""Sensor platform for samsungehs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.helpers import device_registry as dr
from homeassistant.const import UnitOfTemperature, UnitOfFrequency, REVOLUTIONS_PER_MINUTE, EntityCategory
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass, SensorStateClass 

from .entity import SamsungEhsEntity

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SamsungEhsDataUpdateCoordinator
from .data import SamsungEhsConfigEntry
from pysamsungnasa.device import NasaDevice
from pysamsungnasa.protocol.enum import AddressClass


@dataclass(kw_only=True, frozen=True)
class SamsungEhsSensorEntityDescription(SensorEntityDescription):
    """Description for Samsung EHS sensor entities."""
    message_number: int | None = None
    value_fn: Callable[[SamsungEhsEntity], str] | None = None

# Define entiry descriptions for the outdoor unit
OUTDOOR_ENTITY_DESCRIPTIONS = (
    SamsungEhsSensorEntityDescription(
        key="outdoor_top_sensor_temperature_1",
        name="Outdoor Top Sensor Temperature 1",
        message_number=0x8280,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    SamsungEhsSensorEntityDescription(
        key="outdoor_compressor_target_frequency",
        name="Outdoor Compressor Target Frequency",
        message_number=0x8237,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ
    ),
    SamsungEhsSensorEntityDescription(
        key="outdoor_fan_rpm",
        name="Outdoor Fan RPM",
        message_number=0x823d,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE
    ),
    SamsungEhsSensorEntityDescription(
        key="last_packet_received",
        name="Last Packet Received",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda entity: entity._device.last_packet_time
    )
)

# Define entiry descriptions for an indoor unit
INDOOR_ENTITY_DESCRIPTIONS = (
    SamsungEhsSensorEntityDescription(
        key="indoor_dhw_target_temperature",
        name="DHW Target Temperature",
        message_number=0x4235,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    SamsungEhsSensorEntityDescription(
        key="indoor_dhw_current_temperature",
        name="DHW Current Temperature",
        message_number=0x4237,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    SamsungEhsSensorEntityDescription(
        key="indoor_flow_temperature",
        name="Flow Temperature",
        message_number=0x4238,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    SamsungEhsSensorEntityDescription(
        key="last_packet_received",
        name="Last Packet Received",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda entity: entity._device.last_packet_time
    )
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Register devices in the device registry
    for subentry in entry.subentries.values():
        async_add_entities(
            [SamsungEhsAvailableAttributesSensor(
                coordinator=entry.runtime_data.coordinator,
                subentry=subentry
            )]
        )
        if subentry.data["address"].startswith("10"):
            # Add outdoor sensors
            async_add_entities(
                (
                    SamsungEhsSensor(
                        coordinator=entry.runtime_data.coordinator,
                        entity_description=entity_description,
                        subentry=subentry
                    )
                    for entity_description in OUTDOOR_ENTITY_DESCRIPTIONS
                ),
                config_subentry_id=subentry.subentry_id
            )
        if subentry.data["address"].startswith("20"):
            async_add_entities(
                (
                    SamsungEhsSensor(
                        coordinator=entry.runtime_data.coordinator,
                        entity_description=entity_description,
                        subentry=subentry
                    )
                    for entity_description in INDOOR_ENTITY_DESCRIPTIONS
                ),
                config_subentry_id=subentry.subentry_id
            )

class SamsungEhsAvailableAttributesSensor(SamsungEhsEntity, SensorEntity):
    """SamsungEHS available attributes sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_name = "Available Attributes"

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        subentry
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(
            coordinator,
            subentry=subentry,
            message_number=None,
            key="available_attributes"
        )

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self._device is not None

    @property
    def native_value(self) -> int:
        """Return the native value."""
        if self._device is None:
            return 0
        return len(self._device.attributes)

    @property
    def extra_state_attributes(self) -> dict[int, Any]:
        """Return extra state attributes."""
        if self._device is None:
            return {}
        return self._device.attributes

class SamsungEhsSensor(SamsungEhsEntity, SensorEntity):
    """samsungehs Sensor class."""

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        entity_description: SamsungEhsSensorEntityDescription,
        subentry
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(
            coordinator,
            subentry=subentry,
            message_number=entity_description.message_number,
            key=entity_description.key
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> int | float | None:
        """Return the native value."""
        if self._device is None:
            return None
        if self._message_number is None and self.entity_description.value_fn is None:
            return None
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(self)
        return self._device.attributes.get(self._message_number, {}).get("value")

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        if self._device is None:
            return False
        if self.entity_description.value_fn is not None:
            return True
        return (self.coordinator.config_entry.runtime_data.client.client.is_connected and
                self._message_number in self._device.attributes)
