"""DataUpdateCoordinator for samsungehs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    from .data import SamsungEhsConfigEntry

class SamsungEhsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Samsung NASA."""

    known_devices: set[str] = set()
    messages_to_read: dict[str, list[int]] = {}
    config_entry: SamsungEhsConfigEntry

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        if not self.config_entry.runtime_data.client.client.is_connected:
            # Attempt to reconnect
            await self.config_entry.runtime_data.client.start()
        # for dest, msgs in self.messages_to_read.items():
        #     await self.config_entry.runtime_data.client.client.nasa_read(
        #         msgs=msgs,
        #         destination=dest
        #     )
        return True

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        await self.config_entry.runtime_data.client.start()
        return await super()._async_setup()
