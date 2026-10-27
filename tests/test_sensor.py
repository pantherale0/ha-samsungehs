"""Sensor state publication, units, availability and registry metadata."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pysamsungnasa.protocol.factory.messages.indoor import In3WayValveMessage
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from . import Report, entity_id


@pytest.mark.parametrize(
    "platform",
    [
        Platform(value)
        for value in (
            "sensor",
            "binary_sensor",
            "climate",
            "water_heater",
            "switch",
            "number",
            "select",
        )
    ],
)
async def test_inventory(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_nasa: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    platform: Platform,
) -> None:
    """Review all registered states, names and metadata for every platform."""
    with patch("custom_components.samsungehs.PLATFORMS", [platform]):
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("indoor_reports")
@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("water_law_target_temperature", "35.0"),
        ("water_law_offset", "2.0"),
        ("dhw_tank_temperature", "37.4"),
        ("three_way_valve", "room"),
        ("room_temperature", "20.5"),
    ],
)
async def test_indoor_values(hass: HomeAssistant, key: str, expected: str) -> None:
    """Literal reported values reach the HA state machine."""
    assert hass.states.get(entity_id(hass, "sensor", key)).state == expected


@pytest.mark.usefixtures("indoor_reports")
async def test_updates(hass: HomeAssistant, report: Report) -> None:
    """Device callbacks change values, including zero and valve states."""
    report("200000", 0x4067, "01")
    report("200000", 0x4248, "0000")
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "sensor", "three_way_valve")).state == "tank"
    assert hass.states.get(entity_id(hass, "sensor", "water_law_offset")).state == "0.0"


async def test_fahrenheit_delta(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_nasa: MagicMock,
    report: Report,
) -> None:
    """An offset is converted as a temperature difference."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity_options(
        entity_id(hass, "sensor", "water_law_offset"),
        "sensor",
        {"unit_of_measurement": "°F"},
    )
    report("200000", 0x4248, "0014")
    await hass.async_block_till_done()
    state = hass.states.get(entity_id(hass, "sensor", "water_law_offset"))
    assert state.state == "3.6"
    assert state.attributes["unit_of_measurement"] == "°F"
    assert state.attributes["device_class"] == "temperature_delta"


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize(
    ("key", "message_id", "payload", "expected"),
    [
        ("operation_status", 0x8001, "02", "op_normal"),
        ("defrost_status", 0x8061, "00", "no_defrost_operation"),
        ("defrost_stage", 0x8247, "00", "0.0"),
        ("discharge_temperature", 0x8280, "01f4", "50.0"),
        ("outdoor_current", 0x8217, "000a", "1.0"),
        ("supply_voltage", 0x24FC, "00e6", "230.0"),
    ],
)
async def test_outdoor(
    hass: HomeAssistant,
    report: Report,
    key: str,
    message_id: int,
    payload: str,
    expected: str,
) -> None:
    """Outdoor diagnostics expose the expected states and category."""
    report("100000", message_id, payload)
    await hass.async_block_till_done()
    target = entity_id(hass, "sensor", key, "100000")
    assert hass.states.get(target).state == expected
    assert er.async_get(hass).async_get(target).entity_category == "diagnostic"


@pytest.mark.usefixtures("indoor_reports")
async def test_connection_and_removed_device(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Lost connections and disappearing devices publish unavailable states."""
    client = mock_nasa.return_value
    target = entity_id(hass, "sensor", "dhw_tank_temperature")
    client.client._is_connected = False
    integration.runtime_data.coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(target).state == "unavailable"
    client.client._is_connected = True
    removed = client.devices.pop("200000")
    integration.runtime_data.coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(target).state == "unavailable"
    client.devices["200000"] = removed


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize("payload", [None, "02"])
async def test_unknown_valve(hass: HomeAssistant, report: Report, payload: str) -> None:
    """Unknown or unrecognized valve values cannot display a valid position."""
    report("200000", 0x4067, payload)
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "sensor", "three_way_valve")).state == "unknown"
    )


@pytest.mark.usefixtures("integration")
async def test_invalid_cached_valve(
    hass: HomeAssistant, mock_nasa: MagicMock, report: Report
) -> None:
    """An unsupported cached valve enum cannot become a valid room/tank state."""
    mock_nasa.return_value.devices["200000"].attributes[0x4067] = In3WayValveMessage(
        value=2
    )
    report("200000", 0x4203, "00cd")
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "sensor", "three_way_valve")).state == "unknown"
    )


@pytest.mark.usefixtures("integration")
async def test_unknown_outdoor_enum(hass: HomeAssistant, report: Report) -> None:
    """A null outdoor report is unknown instead of a fabricated operation mode."""
    report("100000", 0x8001, None)
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "sensor", "operation_status", "100000")).state
        == "unknown"
    )
