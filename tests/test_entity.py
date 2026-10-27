"""Entity registry identities, metadata and subscription cleanup."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pysamsungnasa.protocol.factory.messages import MESSAGE_PARSERS
from pysamsungnasa.protocol.factory.messages.basic import (
    ProductModelName,
    SerialNumber,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import DOMAIN, entity_id


async def test_device_info(hass: HomeAssistant, integration: MockConfigEntry) -> None:
    """All platforms share the correct subentry device and stable metadata."""
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "200000_200000"), "connection"
    )
    assert device is not None
    assert (
        device.manufacturer,
        device.model,
        device.model_id,
        device.sw_version,
        device.serial_number,
    ) == ("Samsung", "AE080", "EHS", "1.0", "TEST-SERIAL")
    assert device.config_entry_id == integration.entry_id
    assert device.config_subentry_id == "200000"
    registered = er.async_get(hass).async_get(entity_id(hass, "climate", "heating"))
    assert registered.device_id == device.id
    assert registered.config_subentry_id == "200000"
    assert registered.unique_id == "200000_200000_heating"


async def test_parser_cleanup(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """No cross-device parser callbacks remain after unload."""
    assert mock_nasa.return_value.parser._packet_listeners[0x8001]
    await hass.config_entries.async_unload(integration.entry_id)
    assert not any(mock_nasa.return_value.parser._packet_listeners.values())


async def test_missing_identity(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Unknown model and sentinel serial values use safe registry defaults."""
    for device in mock_nasa.return_value.devices.values():
        device.attributes[ProductModelName.MESSAGE_ID] = ProductModelName(value=None)
        device.attributes[SerialNumber.MESSAGE_ID] = SerialNumber(
            value="ffffffffffffffffffffffffffffffff"
        )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "200000_200000"), "connection"
    )
    assert device.model == "Samsung EHS"
    assert device.model_id is None
    assert device.serial_number is None


async def test_disable_one_energy_sensor(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Disabling one sensor keeps the other sensor's parser subscription alive."""
    registry = er.async_get(hass)
    registry.async_update_entity(
        entity_id(hass, "sensor", "power_generation", "100000"),
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    await hass.async_block_till_done()
    listeners = mock_nasa.return_value.parser._packet_listeners[0x4427]
    assert listeners
    for callback in list(listeners):
        callback(
            messageNumber=0x4427,
            packet=MESSAGE_PARSERS[0x4427](value=12.0),
            dest="510000",
            formattedMessageNumber="0x4427",
        )
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "sensor", "energy_generation", "100000")).state
        == "12.0"
    )
