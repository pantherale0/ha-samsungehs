"""DataUpdateCoordinator for samsungehs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    from .data import SamsungEhsConfigEntry


class SamsungEhsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Samsung NASA."""

    config_entry: SamsungEhsConfigEntry
    _first_refresh: bool = True

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        if not self.config_entry.runtime_data.client.client.is_connected:
            # Attempt to reconnect
            await self.config_entry.runtime_data.client.start()
        if self._first_refresh:
            # Add all messages that need to be read on first run
            for (
                device_address,
                messages,
            ) in self.config_entry.runtime_data.first_run_messages.items():
                for i in range(0, len(messages), 10):
                    batch = messages[i : i + 10]
                    await self.config_entry.runtime_data.client.client.nasa_read(
                        batch, device_address
                    )
            self._first_refresh = False

        # Messages can only be read in batches of 10
        for (
            device_address,
            messages,
        ) in self.config_entry.runtime_data.messages_to_read.items():
            for i in range(0, len(messages), 10):
                batch = messages[i : i + 10]
                await self.config_entry.runtime_data.client.client.nasa_read(
                    batch, device_address
                )

        return True

    async def write_message(
        self, device_address: str, request_type: Any, message: Any
    ) -> None:
        """Write a message to the device."""
        await self.config_entry.runtime_data.client.send_message(
            device_address,
            request_type=request_type,
            messages=[message],
        )
