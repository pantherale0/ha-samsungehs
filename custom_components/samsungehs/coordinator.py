"""DataUpdateCoordinator for samsungehs."""

from __future__ import annotations

from math import e
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
            for entry in self.config_entry.subentries.values():
                if entry.unique_id is None:
                    continue
                if entry.unique_id not in self.config_entry.runtime_data.client.devices:
                    continue
                await self.config_entry.runtime_data.client.devices[
                    entry.unique_id
                ].get_configuration()
            self._first_refresh = False
        return True
