"""Diagnostics support for Samsung EHS."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_PORT
from homeassistant.helpers.redact import async_redact_data
from pysamsungnasa.protocol.factory.messages.basic import SerialNumber

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SamsungEhsConfigEntry

TO_REDACT = {CONF_DEVICE, CONF_HOST, CONF_PORT, "address"}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: SamsungEhsConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client = entry.runtime_data.client
    coordinator = entry.runtime_data.coordinator

    def get_device_attributes(device_address: str | None) -> dict[str, Any]:
        """Return diagnostics for a device."""
        device = client.devices.get(device_address) if device_address else None
        if device is None:
            return {}
        return {
            hex(attribute_id): (
                attribute.as_dict | {"value": "**REDACTED**"}
                if attribute_id == SerialNumber.MESSAGE_ID
                else attribute.as_dict
            )
            for attribute_id, attribute in device.attributes.items()
        }

    return {
        "config_entry": {
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
            "subentries": [
                {
                    "type": subentry.subentry_type,
                    "data": async_redact_data(subentry.data, TO_REDACT),
                    "attributes": get_device_attributes(subentry.unique_id),
                }
                for subentry in entry.subentries.values()
            ],
        },
        "runtime_data": {
            "client": {
                "connected": client.client.is_connected,
                "device_count": len(client.devices),
            },
            "coordinator": {
                "last_update_success": coordinator.last_update_success,
                "update_interval_seconds": coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None,
            },
        },
    }
