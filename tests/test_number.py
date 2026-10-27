"""Number actions validate and write device settings through Home Assistant."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pysamsungnasa.protocol.factory.messages.indoor import InFsv5051

from . import Report, entity_id

pytestmark = pytest.mark.usefixtures("integration")


@pytest.mark.parametrize(
    ("key", "message_id", "payload", "expected"),
    [
        ("fsv2011_outdoor_temp_heating_max", 16980, "ff9c", -10.0),
        ("fsv2012_outdoor_temp_heating_min", 16981, "0096", 15.0),
        ("fsv2031_water_out_temp_wl2_heating_max", 16984, "01f4", 50.0),
        ("fsv2032_water_out_temp_wl2_heating_min", 16985, "015e", 35.0),
        ("fsv3083_bsh_capacity", 17135, "0003", 3.0),
    ],
)
async def test_fsv(
    hass: HomeAssistant,
    mock_nasa: MagicMock,
    report: Report,
    key: str,
    message_id: int,
    payload: str,
    expected: float,
) -> None:
    """Signed temperatures and FSV values round-trip without index arithmetic."""
    report("200000", message_id, payload)
    await hass.async_block_till_done()
    target = entity_id(hass, "number", key)
    assert float(hass.states.get(target).state) == expected
    await hass.services.async_call(
        "number", "set_value", {"entity_id": target, "value": expected}, blocking=True
    )
    call = mock_nasa.return_value.devices["200000"].write_attribute.await_args
    assert message_id == call.args[0].MESSAGE_ID
    assert call.kwargs == {"value": expected}


async def test_invalid_value(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """HA rejects out-of-range numbers before a device write."""
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": entity_id(hass, "number", "fsv3083_bsh_capacity"),
                "value": 10000,
            },
            blocking=True,
        )
    mock_nasa.return_value.devices["200000"].write_attribute.assert_not_awaited()


async def test_custom_write(
    hass: HomeAssistant, mock_nasa: MagicMock, report: Report
) -> None:
    """Frequency control uses the dictionary expected by the library."""
    report("200000", InFsv5051.MESSAGE_ID, "01")
    await hass.async_block_till_done()
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": entity_id(hass, "number", "frequency_ratio_control_percent"),
            "value": 50,
        },
        blocking=True,
    )
    call = mock_nasa.return_value.devices["200000"].write_attribute.await_args
    assert call.args[0].MESSAGE_ID == 0x42F1
    assert call.kwargs == {"value": {"frequency_ratio_percent": 50}}


async def test_frequency_reading(hass: HomeAssistant, report: Report) -> None:
    """Structured frequency percentages are read while FSV5051 is enabled."""
    report("200000", InFsv5051.MESSAGE_ID, "01")
    report("200000", 0x42F1, "6401")
    await hass.async_block_till_done()
    assert (
        hass.states.get(
            entity_id(hass, "number", "frequency_ratio_control_percent")
        ).state
        == "100"
    )


async def test_null_number(hass: HomeAssistant, report: Report) -> None:
    """A parsed missing number remains unknown rather than becoming zero."""
    report("200000", 16980, "")
    await hass.async_block_till_done()
    assert (
        hass.states.get(
            entity_id(hass, "number", "fsv2011_outdoor_temp_heating_max")
        ).state
        == "unknown"
    )
