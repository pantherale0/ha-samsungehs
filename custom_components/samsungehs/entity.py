"""BlueprintEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SamsungEhsDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from pysamsungnasa.device import IndoorNasaDevice, NasaDevice, OutdoorNasaDevice


class SamsungEhsEntity(CoordinatorEntity[SamsungEhsDataUpdateCoordinator]):
    """Samsung EHS class."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        message_number: int | None,
        key: str,
        subentry: ConfigSubentry | None,
        requires_read: bool = False,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        address = None
        if subentry is not None:
            entry_id = subentry.subentry_id
            address = subentry.unique_id
        if address is None:
            self._attr_unique_id = f"{entry_id}_{key}"
            self._device_address = None
        else:
            self._device_address = address
            self._attr_unique_id = f"{entry_id}_{self._device_address}_{key}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry_id}_{self._device_address}")},
                manufacturer="Samsung",
                name=self._device_address,
            )
        self._message_number = message_number
        if (
            requires_read
            and self._device_address is not None
            and self._message_number is not None
        ):
            coordinator.config_entry.runtime_data.messages_to_read.setdefault(
                self._device_address, []
            ).append(self._message_number)

    @property
    def _device(self) -> IndoorNasaDevice | OutdoorNasaDevice | NasaDevice | None:
        """Return the device associated with this entity."""
        if self._device_address is None:
            return None
        if (
            self._device_address
            not in self.coordinator.config_entry.runtime_data.client.devices
        ):
            return None
        return self.coordinator.config_entry.runtime_data.client.devices[
            self._device_address
        ]

    async def async_added_to_hass(self) -> None:
        """Call when the entity is added to HASS."""
        await super().async_added_to_hass()
        if self._message_number is not None and self._device_address is not None:
            await self.coordinator.config_entry.runtime_data.client.client.nasa_read(
                msgs=[self._message_number], destination=self._device_address
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
