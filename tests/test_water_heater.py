"""Water heater operation, readings and service writes."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pysamsungnasa.protocol.enum import DataType, DhwOpMode
from pysamsungnasa.protocol.factory.messages.indoor import (
    DhwTargetTemperature,
    InDhwOpMode,
    InDhwWaterHeaterPower,
)

from . import entity_id

pytestmark = [
    pytest.mark.usefixtures("indoor_reports"),
    pytest.mark.platforms("water_heater"),
]


async def test_readings(hass: HomeAssistant) -> None:
    """The HA entity exposes reported current and target temperatures."""
    state = hass.states.get(entity_id(hass, "water_heater", "dhw"))
    assert state.attributes["current_temperature"] == 37.4
    assert state.attributes["temperature"] == 50.0
    assert state.state == "eco"


async def test_temperature(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """HA's set-temperature action writes a NASA request."""
    await hass.services.async_call(
        "water_heater",
        "set_temperature",
        {"entity_id": entity_id(hass, "water_heater", "dhw"), "temperature": 50},
        blocking=True,
    )
    mock_nasa.return_value.devices["200000"].write_attribute.assert_awaited_once_with(
        DhwTargetTemperature, 50, mode=DataType.REQUEST
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("eco", DhwOpMode.ECO),
        ("heat_pump", DhwOpMode.STANDARD),
        ("performance", DhwOpMode.POWER),
        ("electric", DhwOpMode.FORCE),
    ],
)
async def test_operation(
    hass: HomeAssistant, mock_nasa: MagicMock, mode: str, expected: DhwOpMode
) -> None:
    """Selecting an operation powers DHW on and writes the correct enum."""
    await hass.services.async_call(
        "water_heater",
        "set_operation_mode",
        {"entity_id": entity_id(hass, "water_heater", "dhw"), "operation_mode": mode},
        blocking=True,
    )
    mock_nasa.return_value.devices["200000"].write_attributes.assert_awaited_once_with(
        {InDhwWaterHeaterPower: True, InDhwOpMode: expected}, mode=DataType.REQUEST
    )


@pytest.mark.parametrize(
    ("action", "value"),
    [("turn_on", True), ("turn_off", False), ("set_operation_mode", False)],
)
async def test_power(
    hass: HomeAssistant, mock_nasa: MagicMock, action: str, *, value: bool
) -> None:
    """Both the off operation and explicit power actions reach the device."""
    data = {"entity_id": entity_id(hass, "water_heater", "dhw")}
    if action == "set_operation_mode":
        data["operation_mode"] = "off"
    await hass.services.async_call("water_heater", action, data, blocking=True)
    mock_nasa.return_value.devices["200000"].write_attribute.assert_awaited_once_with(
        InDhwWaterHeaterPower, value=value
    )
