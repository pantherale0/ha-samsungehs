"""BlueprintEntity class."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pysamsungnasa.device import NasaDevice

from .const import DOMAIN
from .coordinator import SamsungEhsDataUpdateCoordinator


class SamsungEhsEntity(CoordinatorEntity[SamsungEhsDataUpdateCoordinator]):
    """Samsung EHS class."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        message_number: int | None,
        key: str,
        subentry: ConfigSubentry | None,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        address = None
        if subentry is not None:
            entry_id = subentry.subentry_id
            address = subentry.data["address"]
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

    @property
    def _device(self) -> NasaDevice | None:
        """Return the device associated with this entity."""
        if self._device_address is None:
            return None
        return self.coordinator.config_entry.runtime_data.client.devices.get(
            self._device_address
        )

    def _callback(self, *_):
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._message_number is not None and self._device_address is not None:
            self.coordinator.messages_to_read.setdefault(
                self._device_address, []
            ).append(self._message_number)
            await self.coordinator.config_entry.runtime_data.client.client.nasa_read(
                msgs=[self._message_number],
            )
        if self._device is None:
            return

        return self._device.add_device_callback(self._callback)

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        if self._device is None:
            return
        return self._device.remove_device_callback(self._callback)
