"""Handlers to register and manage Samsung EHS devices in device registry."""

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from pysamsungnasa.device import NasaDevice

from .data import SamsungEhsConfigEntry


async def async_trigger_discovered_device(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
    device: NasaDevice,
) -> None:
    """Create a discovered device in Home Assistant from a NasaDevice."""
    # Register device in the config entry options and reload the entry
    address = device.address
    if address in entry.options.get("device_addresses", []):
        return
    device_addresses = list(entry.options.get("device_addresses", []))
    device_addresses.append(address)
    hass.config_entries.async_add_subentry(
        entry=entry,
        subentry=ConfigSubentry(
            subentry_type="device",
            title=address,
            unique_id=address,
            data={},  # type: ignore[arg-type]
        ),
    )
    hass.config_entries.async_schedule_reload(entry.entry_id)
