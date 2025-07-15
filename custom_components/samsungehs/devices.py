"""Handlers to register and manage Samsung EHS devices in device registry."""

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import entity_platform as ep

from pysamsungnasa.device import NasaDevice
from .data import SamsungEhsConfigEntry

async def async_setup_devices(
    entry: SamsungEhsConfigEntry,
    device: NasaDevice
):
    """Set up devices in the device registry."""
    hass = entry.runtime_data.coordinator.hass
    device_registry = dr.async_get(hass)

    @callback
    def add_device(
        device: NasaDevice,
        entry: SamsungEhsConfigEntry,
    ):
        """Add a device into the device registry."""
        return device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(entry.domain, device.address)},
            name=device.address,
            model=device.device_type.name,
            manufacturer="Samsung",
        )
    new_device_added = False
    if device.address not in entry.runtime_data.coordinator.known_devices:
        # add the device to the device registry
        entry.runtime_data.coordinator.known_devices.add(device.address)
        new_device_added = True
    new_device = add_device(
        device=device,
        entry=entry,
    )
    # Update callback handler on all entities in device
    entities = er.async_entries_for_device(
        registry=er.async_get(hass),
        device_id=new_device.id
    )
    for entity in entities:
        for platform in ep.async_get_platforms(hass, entity.platform):
            entity = platform.entities.get(entity.entity_id)
            if entity is not None:
                await entity.async_added_to_hass()
                await entity.async_update_ha_state()
