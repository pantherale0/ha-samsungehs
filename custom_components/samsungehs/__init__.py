"""
Custom integration to integrate samsungehs with Home Assistant.

For more details about this integration, please refer to
https://github.com/pantherale0/samsungehs
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from pysamsungnasa import SamsungNasa
from pysamsungnasa.protocol.factory.messages.basic import (
    DbCodeMiComMainMessage,
    ProductModelName,
    SerialNumber,
)

from .const import DOMAIN, LOGGER
from .coordinator import SamsungEhsDataUpdateCoordinator
from .data import SamsungEhsConfigEntry, SamsungEhsData
from .devices import async_trigger_discovered_device

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pysamsungnasa.device import NasaDevice

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.WATER_HEATER,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = SamsungEhsDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=15),
    )

    async def trigger_new_device(device: NasaDevice) -> None:
        await async_trigger_discovered_device(
            hass=hass,
            entry=entry,
            device=device,
        )

    client = SamsungNasa(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        config={
            "device_addresses": [
                subentry.unique_id for subentry in entry.subentries.values()
            ],
        },
        new_device_event_handler=trigger_new_device,
    )
    entry.runtime_data = SamsungEhsData(
        client=client,
        coordinator=coordinator,
    )

    try:
        # Ensure connection is established and basic info is read
        await client.start()
        for subentry in entry.subentries.values():
            if not subentry.unique_id:
                continue
            await client.devices[subentry.unique_id].get_attribute(
                ProductModelName, requires_read=True
            )
            await client.devices[subentry.unique_id].get_attribute(
                SerialNumber, requires_read=True
            )
            await client.devices[subentry.unique_id].get_attribute(
                DbCodeMiComMainMessage, requires_read=True
            )
    except Exception as ex:
        raise ConfigEntryNotReady from ex
    # Setup platforms first to populate a list of messages to retrieve
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
