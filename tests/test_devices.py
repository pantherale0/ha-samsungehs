"""Discovery registers each physical device once per connection."""

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pysamsungnasa import SamsungNasa
from pysamsungnasa.protocol.factory.messages.indoor import DhwCurrentTemperature
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import DOMAIN


@pytest.mark.parametrize(
    ("address", "added"), [("300000", True), ("200000", False), ("62FF00", False)]
)
async def test_discovery(
    hass: HomeAssistant,
    integration: MockConfigEntry,
    mock_nasa: MagicMock,
    address: str,
    *,
    added: bool,
) -> None:
    """Library discovery creates a subentry only for a new controllable device."""
    client = mock_nasa.return_value
    client._add_device(address)
    callback = mock_nasa.call_args.kwargs["new_device_event_handler"]
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload", return_value=True
    ) as reload:
        await callback(client.devices[address])
        await callback(client.devices[address])
        await hass.async_block_till_done()
    assert len(integration.subentries) == (3 if added else 2)
    assert reload.await_count == (1 if added else 0)


async def test_two_connections(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_nasa: MagicMock,
    nasa_client_factory: Callable[[str, list[str]], SamsungNasa],
) -> None:
    """Identical addresses on two connections never share reports or commands."""
    first = mock_nasa.return_value
    second = nasa_client_factory("socket://192.0.2.2:8888", ["200000"])
    mock_nasa.side_effect = [first, second]
    other = MockConfigEntry(
        domain=DOMAIN,
        data={"device": "socket://192.0.2.2:8888"},
        version=2,
        entry_id="second",
        subentries_data=[
            {
                "subentry_id": "secondindoor",
                "subentry_type": "device",
                "unique_id": "200000",
                "title": "200000",
                "data": {},
            }
        ],
    )
    mock_config_entry.add_to_hass(hass)
    other.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "secondindoor_200000"), other.entry_id
    )
    assert device is not None
    await hass.services.async_call(
        DOMAIN,
        "write_attribute",
        {"device_id": device.id, "attribute": 0x4201, "value": 22},
        blocking=True,
    )
    assert second.devices["200000"].write_attribute.await_count == 1
    first.devices["200000"].write_attribute.assert_not_awaited()
    await hass.services.async_call(
        DOMAIN,
        "set_external_room_temperature",
        {"config_entry_id": other.entry_id, "zone": 1, "enabled": False},
        blocking=True,
    )
    second.send_message.assert_awaited_once()
    first.send_message.assert_not_awaited()
    second.devices["200000"].handle_packet(
        messageNumber=0x4237,
        packet=DhwCurrentTemperature(value=42.0),
        dest="510000",
        formattedMessageNumber="0x4237",
    )
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    first_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "200000_200000_dhw_tank_temperature"
    )
    second_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "secondindoor_200000_dhw_tank_temperature"
    )
    assert hass.states.get(first_id).state == "unavailable"
    assert hass.states.get(second_id).state == "42.0"
