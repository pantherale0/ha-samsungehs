"""Services for Samsung EHS integration."""

import logging
import math
from enum import StrEnum
from typing import TYPE_CHECKING

import probatio as vol
from homeassistant.const import ATTR_CONFIG_ENTRY_ID, ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import service
from pysamsungnasa.protocol.enum import DataType
from pysamsungnasa.protocol.factory.messages import MESSAGE_PARSERS
from pysamsungnasa.protocol.factory.messages.indoor import (
    InRoomTempSensorMessage,
    InRoomTempSensorZone2Message,
    InRoomTempZone1Message,
    InRoomTempZone2Message,
)
from pysamsungnasa.protocol.factory.types import BaseMessage, RawMessage, SendMessage

from .const import DOMAIN

if TYPE_CHECKING:
    from .data import SamsungEhsConfigEntry

_LOGGER = logging.getLogger(__name__)


class SamsungEHSService(StrEnum):
    """Samsung EHS Services."""

    READ_ATTRIBUTE = "read_attribute"
    WRITE_ATTRIBUTE = "write_attribute"
    SET_EXTERNAL_ROOM_TEMPERATURE = "set_external_room_temperature"


def _validate_external_temperature(value: object) -> float:
    """Validate a Celsius value that fits the signed NASA temperature field."""
    if isinstance(value, bool):
        message = "Temperature must be a number"
        raise vol.Invalid(message)
    temperature = vol.Coerce(float)(value)
    if not math.isfinite(temperature):
        message = "Temperature must be finite"
        raise vol.Invalid(message)
    vol.Range(min=-3276.8, max=3276.7)(temperature)
    return temperature


def _validate_zone(value: object) -> int:
    """Accept a zone number or its selector representation."""
    if type(value) not in (int, str) or str(value) not in ("1", "2"):
        message = "Zone must be 1 or 2"
        raise vol.Invalid(message)
    return int(value)


EXTERNAL_ROOM_TEMPERATURE_SCHEMA = {
    vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required("zone"): _validate_zone,
    vol.Required("enabled"): cv.boolean,
    vol.Optional("temperature"): _validate_external_temperature,
}


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Samsung EHS integration."""
    hass.services.async_register(
        DOMAIN,
        SamsungEHSService.SET_EXTERNAL_ROOM_TEMPERATURE,
        async_set_external_room_temperature_service,
        schema=vol.Schema(EXTERNAL_ROOM_TEMPERATURE_SCHEMA),
    )
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


async def async_set_external_room_temperature_service(call: ServiceCall) -> None:
    """Broadcast one external room sensor notification on the selected bus."""
    entry: SamsungEhsConfigEntry = service.async_get_config_entry(
        call.hass, DOMAIN, call.data[ATTR_CONFIG_ENTRY_ID]
    )
    enabled: bool = call.data["enabled"]
    temperature: float | None = call.data.get("temperature")
    if enabled and temperature is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="external_temperature_required",
        )
    client = entry.runtime_data.client
    if not client.client.is_connected:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="external_temperature_failed",
        )
    sensor_message, temperature_message = (
        (InRoomTempSensorMessage, InRoomTempZone1Message)
        if call.data["zone"] == 1
        else (InRoomTempSensorZone2Message, InRoomTempZone2Message)
    )
    messages = [
        SendMessage(
            MESSAGE_ID=sensor_message.MESSAGE_ID,
            PAYLOAD=sensor_message.to_bytes(enabled),
        )
    ]
    if enabled and temperature is not None:
        messages.append(
            SendMessage(
                MESSAGE_ID=temperature_message.MESSAGE_ID,
                PAYLOAD=round(temperature * 10).to_bytes(2, "big", signed=True),
            )
        )
    try:
        await client.send_message(
            destination="B0FF20",
            request_type=DataType.NOTIFICATION,
            messages=messages,
            source="510000",
        )
    except OSError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="external_temperature_failed",
        ) from err


def _get_device_from_call(call: ServiceCall) -> dr.AnyDeviceEntry:
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


def _get_device_address(device: dr.AnyDeviceEntry) -> str | None:
    """Get device address from device entry."""
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            return identifier[1].split("_")[1]
    return None


def _get_attribute_class_by_id(attribute_id: int) -> type[BaseMessage]:
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
    device: dr.AnyDeviceEntry = _get_device_from_call(call)
    config_entry = call.hass.config_entries.async_get_entry(device.config_entry_id)

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
        attribute,
        requires_read=True,
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
    device: dr.AnyDeviceEntry = _get_device_from_call(call)
    config_entry = call.hass.config_entries.async_get_entry(device.config_entry_id)

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
