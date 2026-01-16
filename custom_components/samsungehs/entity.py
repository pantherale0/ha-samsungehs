"""BlueprintEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pysamsungnasa.protocol.factory.types import BaseMessage

from .const import DOMAIN
from .coordinator import SamsungEhsDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from pysamsungnasa.device import NasaDevice


class SamsungEhsEntity(CoordinatorEntity[SamsungEhsDataUpdateCoordinator]):
    """Samsung EHS class."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        message: type[BaseMessage] | None,
        key: str,
        subentry: ConfigSubentry,
        requires_read: bool = False,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        entry_id = subentry.subentry_id
        assert subentry.unique_id is not None  # noqa: S101
        address = subentry.unique_id
        self._device_address = address
        self._attr_unique_id = f"{entry_id}_{self._device_address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{self._device_address}")},
            manufacturer="Samsung",
            name=self._device_address,
        )
        self._message = message
        if (
            requires_read
            and self._device_address is not None
            and self._message is not None
            and self._message.MESSAGE_ID is not None
        ):
            coordinator.config_entry.runtime_data.messages_to_read.setdefault(
                self._device_address, []
            ).append(self._message.MESSAGE_ID)

    @property
    def _device(self) -> NasaDevice:
        """Return the device associated with this entity."""
        return self.coordinator.config_entry.runtime_data.client.devices[
            self._device_address
        ]

    def get_attribute(
        self, message: type[BaseMessage] | None = None
    ) -> str | int | float | None:
        """Get the attribute value for this entity."""
        if not isinstance(message, type) or (
            not issubclass(message, BaseMessage) and message is not None
        ):
            return None
        message_number = (
            self._message.MESSAGE_ID if message is None else message.MESSAGE_ID
        )
        assert message_number is not None  # noqa: S101
        if self._device is None or message_number is None:
            return None
        attribute = self._device.attributes.get(message_number)
        if attribute is None:
            return None
        return attribute.VALUE

    async def async_added_to_hass(self) -> None:
        """Call when the entity is added to HASS."""
        await super().async_added_to_hass()
        if (
            self._message is not None
            and self._device_address is not None
            and self._message.MESSAGE_ID is not None
        ):
            await self.coordinator.config_entry.runtime_data.client.client.nasa_read(
                msgs=[self._message.MESSAGE_ID], destination=self._device_address
            )
        if self._device is None:
            return

        self._device.add_device_callback(self.async_schedule_update_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Call when the entity is about to be removed from HASS."""
        await super().async_will_remove_from_hass()
        if self._device is None:
            return
        self._device.remove_device_callback(self.async_schedule_update_ha_state)
