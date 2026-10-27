"""Climate states and actions follow the device's temperature-control source."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pysamsungnasa.protocol.enum import DataType, InOperationMode, InOperationPower
from pysamsungnasa.protocol.factory.messages import MESSAGE_PARSERS, indoor
from pysamsungnasa.protocol.factory.messages.outdoor import (
    OutdoorOperationStatusMessage,
)

from . import Report, entity_id

pytestmark = [
    pytest.mark.usefixtures("indoor_reports"),
    pytest.mark.platforms("climate"),
]


@pytest.mark.parametrize(
    (
        "thermostat1",
        "thermostat2",
        "operation",
        "reference",
        "current",
        "target",
        "message_id",
    ),
    [
        ("00", "00", "04", "00", 20.5, 21.0, 0x4201),
        ("00", "00", "01", "01", 33.5, 30.0, 0x4247),
        ("01", "00", "04", "00", 33.5, 2.0, 0x4248),
        ("00", "01", "01", "01", 33.5, 2.0, 0x4248),
        ("00", "00", "00", "00", 33.5, 2.0, 0x4248),
    ],
)
async def test_control_source(
    hass: HomeAssistant,
    mock_nasa: MagicMock,
    report: Report,
    thermostat1: str,
    thermostat2: str,
    operation: str,
    reference: str,
    current: float,
    target: float,
    message_id: int,
) -> None:
    """Literal precedence cases choose both displayed values and command IDs."""
    for message, payload in [
        (0x4095, thermostat1),
        (0x4096, thermostat2),
        (0x4001, operation),
        (0x406F, reference),
    ]:
        report("200000", message, payload)
    await hass.async_block_till_done()
    climate = entity_id(hass, "climate", "heating")
    state = hass.states.get(climate)
    assert state.attributes["current_temperature"] == current
    assert state.attributes["temperature"] == target
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": climate, "temperature": 22.0},
        blocking=True,
    )
    write = mock_nasa.return_value.devices["200000"].write_attribute
    assert message_id == write.await_args.args[0].MESSAGE_ID
    assert write.await_args.args[1] == 22.0
    assert write.await_args.kwargs == {"mode": DataType.REQUEST}


@pytest.mark.parametrize("missing", [0x4095, 0x4096, 0x406F])
@pytest.mark.parametrize("null_value", [False, True])
async def test_missing_inputs(
    hass: HomeAssistant,
    mock_nasa: MagicMock,
    report: Report,
    missing: int,
    *,
    null_value: bool,
) -> None:
    """Unknown control settings cannot send an unsafe setpoint."""
    device = mock_nasa.return_value.devices["200000"]
    if null_value:
        device.attributes[missing] = MESSAGE_PARSERS[missing](value=None)
    else:
        device.attributes.pop(missing)
    report("200000", 0x4201, "00d2")
    await hass.async_block_till_done()
    climate = entity_id(hass, "climate", "heating")
    assert hass.states.get(climate).attributes["temperature"] is None
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": climate, "temperature": 22.0},
        blocking=True,
    )
    device.write_attribute.assert_not_awaited()
    report("200000", missing, "00")
    await hass.async_block_till_done()
    assert hass.states.get(climate).attributes["temperature"] == 21.0


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("heat", InOperationMode.HEAT),
        ("cool", InOperationMode.COOL),
        ("auto", InOperationMode.AUTO),
        ("fan_only", InOperationMode.FAN),
    ],
)
async def test_hvac_mode(
    hass: HomeAssistant, mock_nasa: MagicMock, mode: str, expected: InOperationMode
) -> None:
    """Selecting an HVAC mode writes the mode followed by power on."""
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id(hass, "climate", "heating"), "hvac_mode": mode},
        blocking=True,
    )
    calls = mock_nasa.return_value.devices["200000"].write_attribute.await_args_list
    assert [(c.args[0].MESSAGE_ID, c.args[1]) for c in calls] == [
        (0x4001, expected),
        (0x4000, InOperationPower.ON_STATE_1),
    ]


@pytest.mark.parametrize(
    ("action", "value"),
    [
        ("turn_on", InOperationPower.ON_STATE_1),
        ("turn_off", InOperationPower.OFF),
        ("set_hvac_mode", InOperationPower.OFF),
    ],
)
async def test_power(
    hass: HomeAssistant, mock_nasa: MagicMock, action: str, value: InOperationPower
) -> None:
    """Power actions use the NASA operation-power message."""
    data = {"entity_id": entity_id(hass, "climate", "heating")}
    if action == "set_hvac_mode":
        data["hvac_mode"] = "off"
    await hass.services.async_call("climate", action, data, blocking=True)
    mock_nasa.return_value.devices["200000"].write_attribute.assert_awaited_once_with(
        indoor.InOperationPowerMessage, value
    )


@pytest.mark.parametrize(
    ("power", "mode", "status", "expected"),
    [
        ("00", "04", "00", "off"),
        ("01", "04", "00", "idle"),
        ("01", "04", "02", "heating"),
        ("01", "01", "02", "cooling"),
        ("01", "04", "01", "preheating"),
        ("01", "04", "05", "defrosting"),
        ("01", "04", "1a", "defrosting"),
    ],
)
async def test_hvac_action(
    hass: HomeAssistant,
    mock_nasa: MagicMock,
    report: Report,
    power: str,
    mode: str,
    status: str,
    expected: str,
) -> None:
    """Cross-device parser listeners update the climate's HVAC action."""
    report("200000", 0x4000, power)
    report("200000", 0x4001, mode)

    message = OutdoorOperationStatusMessage.parse_payload(bytes.fromhex(status))
    for callback in list(mock_nasa.return_value.parser._packet_listeners[0x8001]):
        callback(
            messageNumber=0x8001,
            packet=message,
            dest="510000",
            formattedMessageNumber="0x8001",
        )
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, "climate", "heating")).attributes["hvac_action"]
        == expected
    )


@pytest.mark.parametrize("setting", ["01", "02", "03", "04"])
async def test_remote_controller_does_not_override(
    hass: HomeAssistant, report: Report, setting: str
) -> None:
    """FSV2093 cannot change the room reference selected by the thermostats."""
    report("200000", 0x4127, setting)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id(hass, "climate", "heating"))
    assert state.attributes["current_temperature"] == 20.5
    assert state.attributes["temperature"] == 21.0
