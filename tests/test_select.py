"""Select actions expose stable labels and preserve actual enum encodings."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import Report, entity_id

pytestmark = [pytest.mark.usefixtures("integration"), pytest.mark.platforms("select")]


@pytest.mark.parametrize(
    ("key", "message_id", "raw", "label"),
    [
        ("temperature_reference", 16495, "00", "room"),
        ("temperature_reference", 16495, "01", "water out"),
        ("water_law_type_heating", 16531, "01", "floor"),
        ("water_law_type_heating", 16531, "02", "fcu"),
        ("use_thermostat_zone_1", 16533, "00", "not used"),
        ("use_thermostat_zone_1", 16533, "01", "thermostat only"),
        ("remote_controller_room_temp_control", 16679, "01", "room temp only"),
        ("remote_controller_room_temp_control", 16679, "02", "wl interlink pump1"),
        ("remote_controller_room_temp_control", 16679, "03", "wl interlink pump2"),
        ("remote_controller_room_temp_control", 16679, "04", "wl interlink pump3"),
    ],
)
async def test_enum(
    hass: HomeAssistant,
    mock_nasa: MagicMock,
    report: Report,
    key: str,
    message_id: int,
    raw: str,
    label: str,
) -> None:
    """Selecting the displayed option sends its literal byte value."""
    target = entity_id(hass, "select", key)
    assert hass.states.get(target).state == "unknown"
    report("200000", message_id, raw)
    await hass.async_block_till_done()
    assert hass.states.get(target).state == label
    await hass.services.async_call(
        "select", "select_option", {"entity_id": target, "option": label}, blocking=True
    )
    call = mock_nasa.return_value.devices["200000"].write_attribute.await_args
    assert message_id == call.args[0].MESSAGE_ID
    assert call.kwargs["value"].value == int(raw, 16)


async def test_invalid_option(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """The service rejects options not advertised by the entity."""
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "select",
            "select_option",
            {
                "entity_id": entity_id(hass, "select", "temperature_reference"),
                "option": "invalid",
            },
            blocking=True,
        )
    mock_nasa.return_value.devices["200000"].write_attribute.assert_not_awaited()


@pytest.mark.parametrize("payload", [None, "7f"])
async def test_unknown_enum(
    hass: HomeAssistant, report: Report, payload: str | None
) -> None:
    """Absent and unrecognized enum values publish unknown without crashing."""
    report("200000", 0x406F, payload)
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "select", "temperature_reference")).state
        == "unknown"
    )
