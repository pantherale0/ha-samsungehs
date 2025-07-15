"""
Custom integration to integrate samsungehs with Home Assistant.

For more details about this integration, please refer to
https://github.com/pantherale0/samsungehs
"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT, Platform

from pysamsungnasa import SamsungNasa
from pysamsungnasa.config import NasaConfig

from .const import DOMAIN, LOGGER
from .coordinator import SamsungEhsDataUpdateCoordinator
from .devices import async_setup_devices
from .data import SamsungEhsConfigEntry, SamsungEhsData

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.WATER_HEATER
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    def disconnection_handler():
        """Reload the connection when disconnected."""
        if entry.runtime_data:
            hass.async_add_executor_job(entry.runtime_data.client.stop)
            hass.async_add_executor_job(entry.runtime_data.client.start)

    coordinator = SamsungEhsDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=15),
    )
    entry.runtime_data = SamsungEhsData(
        client=SamsungNasa(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            config={
                "client_address": 0x01,
                "device_addresses": [subentry.data["address"] for subentry in entry.subentries.values()]
            },
            disconnect_event_handler=disconnection_handler
        ),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    await entry.runtime_data.client.stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
) -> None:
    """Reload config entry."""
    await entry.runtime_data.client.stop()
    await hass.config_entries.async_reload(entry.entry_id)
