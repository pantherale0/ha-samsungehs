"""Attribute services resolve real registry devices and config entries."""

from unittest.mock import MagicMock

import probatio as vol
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pysamsungnasa.protocol.factory.messages.indoor import InTargetTemperature
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import DOMAIN

pytestmark = pytest.mark.usefixtures("integration")


def indoor_device(hass: HomeAssistant) -> dr.DeviceEntry:
    """Get the device registered by the actual indoor entities."""
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "200000_200000"), "connection"
    )
    assert device is not None
    return device


async def test_read(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """The read service returns a serialized library message."""
    message = InTargetTemperature(value=21.0)
    read = mock_nasa.return_value.devices["200000"].get_attribute
    read.side_effect = None
    read.return_value = message
    read.reset_mock()
    result = await hass.services.async_call(
        DOMAIN,
        "read_attribute",
        {"device_id": indoor_device(hass).id, "attribute": 0x4201},
        blocking=True,
        return_response=True,
    )
    assert result == {
        "message_id": 0x4201,
        "message_name": "Indoor Target Temperature",
        "unit_of_measurement": "C",
        "value": 21.0,
        "is_fsv_message": False,
    }
    read.assert_awaited_once_with(InTargetTemperature, requires_read=True)


@pytest.mark.parametrize("attribute", [0x4201, 0xFFFF])
async def test_write(hass: HomeAssistant, mock_nasa: MagicMock, attribute: int) -> None:
    """Known and raw attributes route to the selected device."""
    await hass.services.async_call(
        DOMAIN,
        "write_attribute",
        {"device_id": indoor_device(hass).id, "attribute": attribute, "value": 22},
        blocking=True,
    )
    call = mock_nasa.return_value.devices["200000"].write_attribute.await_args
    assert attribute == call.args[0].MESSAGE_ID
    assert call.args[1] == 22
    mock_nasa.return_value.devices["100000"].write_attribute.assert_not_awaited()


@pytest.mark.parametrize("action", ["read_attribute", "write_attribute"])
@pytest.mark.parametrize("target", ["missing", "foreign", "unloaded"])
async def test_invalid_device(
    hass: HomeAssistant, mock_nasa: MagicMock, target: str, action: str
) -> None:
    """Invalid registry targets never access a different connection."""
    device_id = "missing"
    if target != "missing":
        other = MockConfigEntry(
            domain="other" if target == "foreign" else DOMAIN, version=2
        )
        other.add_to_hass(hass)
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=other.entry_id, identifiers={("other", "test")}
        )
        device_id = device.id
    data = {"device_id": device_id, "attribute": 0x4201}
    if action == "write_attribute":
        data["value"] = 22
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            action,
            data,
            blocking=True,
            return_response=action == "read_attribute",
        )
    mock_nasa.return_value.devices["200000"].write_attribute.assert_not_awaited()


@pytest.mark.parametrize("action", ["read_attribute", "write_attribute"])
async def test_missing_device_id(hass: HomeAssistant, action: str) -> None:
    """Required service fields are validated by HA."""
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            action,
            {"attribute": 1},
            blocking=True,
            return_response=action == "read_attribute",
        )


@pytest.mark.parametrize("action", ["read_attribute", "write_attribute"])
async def test_unloaded_matching_device(
    hass: HomeAssistant, mock_nasa: MagicMock, action: str
) -> None:
    """A real Samsung identifier must still belong to a loaded connection."""
    other = MockConfigEntry(domain=DOMAIN, version=2)
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={(DOMAIN, "subentry_200000")}
    )
    data = {"device_id": device.id, "attribute": 0x4201}
    if action == "write_attribute":
        data["value"] = 22
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            action,
            data,
            blocking=True,
            return_response=action == "read_attribute",
        )
    mock_nasa.return_value.devices["200000"].write_attribute.assert_not_awaited()


@pytest.mark.parametrize(
    "identifier",
    [("other", "device"), (DOMAIN, "malformed"), (DOMAIN, "subentry_300000")],
)
async def test_invalid_address(
    hass: HomeAssistant, integration: MockConfigEntry, identifier: tuple[str, str]
) -> None:
    """Registry identifiers must resolve to a device on the selected connection."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=integration.entry_id, identifiers={identifier}
    )
    with pytest.raises(ServiceValidationError) as exc:
        await hass.services.async_call(
            DOMAIN,
            "write_attribute",
            {"device_id": device.id, "attribute": 0x4201, "value": 22},
            blocking=True,
        )
    assert exc.value.translation_key == "invalid_device"


async def test_empty_device_id(hass: HomeAssistant) -> None:
    """An empty target produces the integration's translated validation error."""
    with pytest.raises(ServiceValidationError) as exc:
        await hass.services.async_call(
            DOMAIN,
            "write_attribute",
            {"device_id": "", "attribute": 0x4201, "value": 22},
            blocking=True,
        )
    assert exc.value.translation_key == "missing_device_id"
