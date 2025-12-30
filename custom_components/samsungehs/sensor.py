"""Sensor platform for samsungehs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
)

from pysamsungnasa.protocol.factory import MESSAGE_PARSERS

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


@dataclass(frozen=True, kw_only=True)
class SamsungEhsSensorEntityDescription(SensorEntityDescription):
    """Description for Samsung EHS sensor entities."""

    message_number: int | None = None
    value_fn: Callable[[SamsungEhsEntity], Any] | None = None


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Register devices in the device registry
    for subentry in entry.subentries.values():
        async_add_entities(
            [
                SamsungEhsAvailableAttributesSensor(
                    coordinator=entry.runtime_data.coordinator, subentry=subentry
                )
            ],
            config_subentry_id=subentry.subentry_id,
        )
        async_add_entities(
            [
                SamsungEhsSensor(
                    coordinator=entry.runtime_data.coordinator,
                    entity_description=SamsungEhsSensorEntityDescription(
                        key="last_packet_received",
                        device_class=SensorDeviceClass.TIMESTAMP,
                        value_fn=lambda entity: entity._device.last_packet_time,
                    ),
                    subentry=subentry,
                )
            ],
            config_subentry_id=subentry.subentry_id,
        )
        entities = []
        for sensor in subentry.data.get("sensors", []):
            parser = MESSAGE_PARSERS.get(int(sensor))
            if parser is None:
                continue
            entities.append(
                SamsungEhsSensor(
                    coordinator=entry.runtime_data.coordinator,
                    entity_description=SamsungEhsSensorEntityDescription(
                        key=sensor,
                        message_number=int(sensor),
                        name=parser.MESSAGE_NAME,
                        native_unit_of_measurement=parser.UNIT_OF_MEASUREMENT,
                    ),
                    subentry=subentry,
                )
            )
        async_add_entities(
            entities,
            config_subentry_id=subentry.subentry_id,
        )


class SamsungEhsAvailableAttributesSensor(SamsungEhsEntity, SensorEntity):
    """SamsungEHS available attributes sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SamsungEhsDataUpdateCoordinator, subentry: ConfigSubentry
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(
            coordinator,
            subentry=subentry,
            message_number=None,
            key="available_attributes",
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
        return {
            msg_number: {
                "name": value.MESSAGE_NAME,
                "value": value.VALUE,
            }
            for msg_number, value in self._device.attributes.items()
        }


class SamsungEhsSensor(SamsungEhsEntity, SensorEntity):
    """samsungehs Sensor class."""

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
        if self._message_number is None and self.entity_description.value_fn is None:
            return None
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(self)
        if (
            self._message_number is not None
            and self._message_number in self._device.attributes
        ):
            return self._device.attributes.get(self._message_number).VALUE
        return None

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
