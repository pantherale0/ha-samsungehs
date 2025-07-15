"""Samsung EHS Binary Sensor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import AddressClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SamsungEhsEntity
from .coordinator import SamsungEhsDataUpdateCoordinator
from .data import SamsungEhsConfigEntry


@dataclass(frozen=True)
class SamsungEhsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description for Samsung EHS binary sensor entities."""

    message_number: int | None = None
    is_on_fn: Callable[[SamsungEhsEntity], bool] | None = None


INTEGRATION_ENTITY_DESCRIPTIONS = (
    SamsungEhsBinarySensorEntityDescription(
        key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda entity: entity.coordinator.config_entry.runtime_data.client.client.is_connected,
    ),
)

ALL_ENTITY_DESCRIPTIONS = (
    SamsungEhsBinarySensorEntityDescription(
        key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda entity: entity._device is not None,
    ),
)

# Define entity description for outdoor unit
OUTDOOR_ENTITY_DESCRIPTIONS = ()

# Define entiry descriptions for a indoor unit
INDOOR_ENTITY_DESCRIPTIONS = ()


async def async_setup_entry(
    _: HomeAssistant,
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    # Register devices in the device registry
    async_add_entities(
        SamsungEhsBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
            subentry=None,
        )
        for entity_description in INTEGRATION_ENTITY_DESCRIPTIONS
    )
    for subentry in entry.subentries.values():
        async_add_entities(
            (
                SamsungEhsBinarySensor(
                    coordinator=entry.runtime_data.coordinator,
                    entity_description=entity_description,
                    subentry=subentry,
                )
                for entity_description in ALL_ENTITY_DESCRIPTIONS
            ),
            config_subentry_id=subentry.subentry_id,
        )
        address = Address.parse(subentry.data["address"])
        if address.class_id == AddressClass.OUTDOOR:
            # Add outdoor sensors
            async_add_entities(
                (
                    SamsungEhsBinarySensor(
                        coordinator=entry.runtime_data.coordinator,
                        entity_description=entity_description,
                        subentry=subentry,
                    )
                    for entity_description in OUTDOOR_ENTITY_DESCRIPTIONS
                ),
                config_subentry_id=subentry.subentry_id,
            )
        elif address.class_id == AddressClass.INDOOR:
            # Add indoor sensors
            async_add_entities(
                (
                    SamsungEhsBinarySensor(
                        coordinator=entry.runtime_data.coordinator,
                        entity_description=entity_description,
                        subentry=subentry,
                    )
                    for entity_description in INDOOR_ENTITY_DESCRIPTIONS
                ),
                config_subentry_id=subentry.subentry_id,
            )


class SamsungEhsBinarySensor(SamsungEhsEntity, BinarySensorEntity):
    """samsungehs binary_sensor class."""

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        entity_description: SamsungEhsBinarySensorEntityDescription,
        subentry,
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
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        if self.entity_description.is_on_fn is not None:
            return self.entity_description.is_on_fn(self)
        if self._message_number is not None and self._device is not None:
            return self._device.attributes.get(self._message_number, {}).get(
                "value", False
            )
        return False
