"""Services for Samsung EHS integration."""

import logging
from enum import StrEnum
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from pysamsungnasa.protocol.factory.messages import MESSAGE_PARSERS
from pysamsungnasa.protocol.factory.types import BaseMessage, RawMessage

from .const import DOMAIN

if TYPE_CHECKING:
    from .data import SamsungEhsConfigEntry

_LOGGER = logging.getLogger(__name__)


class SamsungEHSService(StrEnum):
    """Samsung EHS Services."""

    READ_ATTRIBUTE = "read_attribute"
    WRITE_ATTRIBUTE = "write_attribute"


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Samsung EHS integration."""
    hass.services.async_register(
        domain=DOMAIN,
        service=SamsungEHSService.READ_ATTRIBUTE,
        service_func=async_read_attribute_service,
        supports_response=SupportsResponse.ONLY,
        schema=vol.Schema(
            {
                vol.Required("attribute"): cv.positive_int,
                vol.Required(ATTR_DEVICE_ID): cv.string,
            }
        ),
    )

    hass.services.async_register(
        domain=DOMAIN,
        service=SamsungEHSService.WRITE_ATTRIBUTE,
        service_func=async_write_attribute_service,
        schema=vol.Schema(
            {
                vol.Required("attribute"): cv.positive_int,
                vol.Required("value"): cv.positive_int,
                vol.Required(ATTR_DEVICE_ID): cv.string,
            }
        ),
    )


def _get_device_from_call(call: ServiceCall) -> dr.DeviceEntry:
    """Get device from service call."""
    device_id = call.data.get(ATTR_DEVICE_ID)
    if not device_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="missing_device_id",
        )

    device_registry = dr.async_get(call.hass)
    device = device_registry.async_get(device_id)
    if not device:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={"device_id": device_id},
        )

    return device


def _get_device_address(device: dr.DeviceEntry) -> str | None:
    """Get device address from device entry."""
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            return identifier[1].split("_")[1]
    return None


def _get_attribute_class_by_id(attribute_id: int) -> BaseMessage:
    """Get attribute class by its ID."""
    attribute = MESSAGE_PARSERS.get(attribute_id)
    if attribute:
        return attribute

    class DummyRawMessage(RawMessage):
        MESSAGE_ID = attribute_id

    return DummyRawMessage


async def async_read_attribute_service(call: ServiceCall) -> dict:
    """Handle read attribute service call."""
    config_entry: SamsungEhsConfigEntry | None = None
    address: str | None = None
    attribute_to_read: int = call.data["attribute"]  # (format in 0xXXXX)
    device: dr.DeviceEntry = _get_device_from_call(call)
    for entry_id in device.config_entries:
        config_entry = call.hass.config_entries.async_get_entry(entry_id)
        if config_entry and config_entry.domain == DOMAIN:
            break

    address = _get_device_address(device)

    if not config_entry or not address:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device",
            translation_placeholders={
                "attribute": str(attribute_to_read),
                "device_id": device.id,
            },
        )

    attribute = _get_attribute_class_by_id(attribute_to_read)
    message = await config_entry.runtime_data.client.devices[address].get_attribute(
        attribute
    )
    _LOGGER.debug(
        "Read attribute '%s' from device '%s': %s",
        str(attribute_to_read),
        address,
        message,
    )
    return message.as_dict


async def async_write_attribute_service(call: ServiceCall) -> None:
    """Handle write attribute service call."""
    config_entry: SamsungEhsConfigEntry | None = None
    address: str | None = None
    attribute_to_write: int = call.data["attribute"]  # (format in 0xXXXX)
    value_to_write: int = call.data["value"]
    device: dr.DeviceEntry = _get_device_from_call(call)
    for entry_id in device.config_entries:
        config_entry = call.hass.config_entries.async_get_entry(entry_id)
        if config_entry and config_entry.domain == DOMAIN:
            break

    address = _get_device_address(device)

    if not config_entry or not address:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device",
            translation_placeholders={
                "attribute": str(attribute_to_write),
                "device_id": device.id,
            },
        )
    attribute = _get_attribute_class_by_id(attribute_to_write)
    await config_entry.runtime_data.client.devices[address].write_attribute(
        attribute, value_to_write
    )
    _LOGGER.debug(
        "Wrote value '%s' to attribute '%s' on device '%s'",
        value_to_write,
        str(attribute_to_write),
        address,
    )
