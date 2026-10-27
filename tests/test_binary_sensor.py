"""Binary sensors update from parsed library reports."""

import pytest
from homeassistant.core import HomeAssistant

from . import Report, entity_id


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize(
    ("address", "key", "message_id", "payload", "expected"),
    [
        ("100000", "defrost", 0x8001, "05", "on"),
        ("100000", "defrost", 0x8001, "1a", "on"),
        ("100000", "defrost", 0x8001, "02", "off"),
        ("100000", "defrost", 0x8001, "00", "off"),
        ("100000", "defrost", 0x8001, "01", "off"),
        ("100000", "four_way_valve", 0x801A, "01", "on"),
        ("100000", "four_way_valve", 0x801A, "00", "off"),
        ("200000", "indoor_thermo_on", 0x4028, "01", "on"),
        ("200000", "indoor_thermo_on", 0x4028, "00", "off"),
    ],
)
async def test_states(
    hass: HomeAssistant,
    report: Report,
    address: str,
    key: str,
    message_id: int,
    payload: str,
    expected: str,
) -> None:
    """Defrost, valves and thermo-on retain their message mappings."""
    report(address, message_id, payload)
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "binary_sensor", key, address)).state
        == expected
    )
