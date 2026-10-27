"""Reported external room readings and flags remain independent per zone."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import Report, entity_id


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize(
    ("zone", "flag", "temperature"), [(1, 0x4076, 0x423A), (2, 0x4118, 0x42DA)]
)
async def test_transitions(
    hass: HomeAssistant, report: Report, zone: int, flag: int, temperature: int
) -> None:
    """A valid reading is visible only while its own flag is enabled."""
    sensor = entity_id(hass, "sensor", f"zone_{zone}_external_room_temperature")
    binary = entity_id(
        hass, "binary_sensor", f"zone_{zone}_external_room_sensor_enabled"
    )
    assert hass.states.get(sensor).state == "unavailable"
    assert hass.states.get(binary).state == "unknown"
    report("200000", temperature, "00d6")
    report("200000", 0x4118 if zone == 1 else 0x4076, "01")
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "unavailable"
    report("200000", flag, "01")
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "21.4"
    assert hass.states.get(binary).state == "on"
    report("200000", flag, "00")
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "unavailable"
    assert hass.states.get(binary).state == "off"
    report("200000", flag, "01")
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "21.4"


async def test_poll_dependencies(integration: MockConfigEntry) -> None:
    """Both zone flags and readings are included in recurring transport reads."""
    assert {0x4076, 0x423A, 0x4118, 0x42DA} <= set(
        integration.runtime_data.messages_to_read["200000"]
    )


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize(
    ("zone", "flag", "temperature"), [(1, 0x4076, 0x423A), (2, 0x4118, 0x42DA)]
)
async def test_enabled_without_reading(
    hass: HomeAssistant, report: Report, zone: int, flag: int, temperature: int
) -> None:
    """A true flag without a valid numeric reading does not expose a temperature."""
    report("200000", flag, "01")
    report("200000", temperature, None)
    await hass.async_block_till_done()
    assert (
        hass.states.get(
            entity_id(hass, "sensor", f"zone_{zone}_external_room_temperature")
        ).state
        == "unavailable"
    )
    assert (
        hass.states.get(
            entity_id(
                hass, "binary_sensor", f"zone_{zone}_external_room_sensor_enabled"
            )
        ).state
        == "on"
    )
