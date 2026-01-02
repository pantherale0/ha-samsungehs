# pylint: disable=E1123
"""Samsung EHS Binary Sensor."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from pysamsungnasa.device import IndoorNasaDevice, NasaDevice, OutdoorNasaDevice
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import (
    AddressClass,
    OutdoorOperationStatus,
    OutdoorPumpOutLoad,
    OutdoorCompressorLoad,
)

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEhsBinarySensorKey(StrEnum):
    """Samsung EHS Binary Sensor Keys."""

    COMPRESSOR_RUNNING = "compressor_running"
    CIRCULATION_PUMP_RUNNING = "circulation_pump_running"
    HP_RUNNING = "hp_running"

    INDOOR_DHW_ON = "indoor_dhw_on"
    INDOOR_HEATING_ON = "indoor_heating_on"
    INDOOR_COOLING_ON = "indoor_cooling_on"


@dataclass(frozen=True, kw_only=True)
class SamsungEhsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description for Samsung EHS binary sensor entities."""

    requires_read: bool = False
    message_number: int | None = None
    is_on_fn: Callable[[IndoorNasaDevice | OutdoorNasaDevice | NasaDevice], bool]


# Define entity description for outdoor unit
OUTDOOR_ENTITY_DESCRIPTIONS = (
    SamsungEhsBinarySensorEntityDescription(
        key=SamsungEhsBinarySensorKey.COMPRESSOR_RUNNING,
        translation_key=SamsungEhsBinarySensorKey.COMPRESSOR_RUNNING,
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda device: 0x8010 in device.attributes
        and device.attributes[0x8010].VALUE == OutdoorCompressorLoad.ON,
        message_number=0x8010,
        requires_read=True,
    ),
    SamsungEhsBinarySensorEntityDescription(
        key=SamsungEhsBinarySensorKey.CIRCULATION_PUMP_RUNNING,
        translation_key=SamsungEhsBinarySensorKey.CIRCULATION_PUMP_RUNNING,
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda device: (
            0x8027 in device.attributes
            and device.attributes[0x8027].VALUE == OutdoorPumpOutLoad.ON
        ),
        message_number=0x8027,
        requires_read=True,
    ),
    SamsungEhsBinarySensorEntityDescription(
        key=SamsungEhsBinarySensorKey.HP_RUNNING,
        translation_key=SamsungEhsBinarySensorKey.HP_RUNNING,
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda device: (
            0x8001 in device.attributes
            and device.attributes[0x8001].VALUE == OutdoorOperationStatus.OP_NORMAL
        ),
        message_number=0x8001,
    ),
)

# Define entiry descriptions for a indoor unit
INDOOR_ENTITY_DESCRIPTIONS = ()


async def async_setup_entry(
    _: HomeAssistant,
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    # Register devices in the device registry
    for subentry in entry.subentries.values():
        if not isinstance(subentry.unique_id, str):
            continue
        address = Address.parse(subentry.unique_id)
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
            requires_read=entity_description.requires_read,
        )
        self.entity_description: SamsungEhsBinarySensorEntityDescription = (
            entity_description
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        if self._device is None:
            return None
        return self.entity_description.is_on_fn(self._device)
