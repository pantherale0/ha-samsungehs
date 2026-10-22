"""Exercise FSV entity reads, writes, and polling registration."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pysamsungnasa.protocol.enum import DataType, InOperationMode
from pysamsungnasa.protocol.factory.messages import indoor
from pysamsungnasa.protocol.factory.types import EnumMessage

from custom_components.samsungehs.climate import SamsungEhsClimate
from custom_components.samsungehs.number import NUMBERS, SamsungEHSNumber
from custom_components.samsungehs.select import SELECTS, SamsungEHSSelect


def make_coordinator() -> SimpleNamespace:
    """Provide a device boundary without connecting to hardware."""
    device = SimpleNamespace(attributes={}, write_attribute=AsyncMock())
    runtime = SimpleNamespace(
        client=SimpleNamespace(
            devices={"200000": device}, client=SimpleNamespace(is_connected=True)
        ),
        messages_to_read={},
    )
    return SimpleNamespace(
        config_entry=SimpleNamespace(runtime_data=runtime), last_update_success=True
    )


SUBENTRY = SimpleNamespace(unique_id="200000", subentry_id="indoor")


@pytest.mark.parametrize("thermostat1", range(5))
@pytest.mark.parametrize("thermostat2", range(5))
@pytest.mark.parametrize("reference", range(2))
@pytest.mark.parametrize(
    "operation", [InOperationMode.HEAT, InOperationMode.COOL, InOperationMode.AUTO]
)
@pytest.mark.parametrize("room_control", [None, 1, 2, 3, 4])
def test_climate_control_priority(
    thermostat1: int,
    thermostat2: int,
    reference: int,
    operation: InOperationMode | None,
    room_control: int | None,
) -> None:
    """Use the reference source unless external thermostats or Auto select WL."""
    coordinator = make_coordinator()
    device = coordinator.config_entry.runtime_data.client.devices["200000"]
    for message, value in (
        (indoor.InOperationModeMessage, operation),
        (indoor.InFsv2091UseThermostat1, thermostat1),
        (indoor.InFsv2092UseThermostat2, thermostat2),
        (indoor.DhwReferenceTemperatureMessage, reference),
        (indoor.InRoomTemperature, 20.5),
        (indoor.InTargetTemperature, 21.0),
        (indoor.IndoorFlowTemperature, 33.5),
        (indoor.InWaterOutletTargetTemperature, 30.0),
        (indoor.InWaterLawTargetTemperature, 2.0),
    ):
        device.attributes[message.MESSAGE_ID] = (
            message.parse_payload(bytes([value]))
            if issubclass(message, EnumMessage)
            else message(value=value)
        )
    if room_control is not None:
        device.attributes[16679] = indoor.InFsv2093.parse_payload(bytes([room_control]))
    if thermostat1 or thermostat2 or operation == InOperationMode.AUTO:
        current, target, write_message = (2.0, 2.0, indoor.InWaterLawTargetTemperature)
    elif reference == 0:
        current, target, write_message = (20.5, 21.0, indoor.InTargetTemperature)
    else:
        current, target, write_message = (
            33.5,
            30.0,
            indoor.InWaterOutletTargetTemperature,
        )
    entity = SamsungEhsClimate(coordinator, SUBENTRY)
    assert entity.current_temperature == current
    assert entity.target_temperature == target
    asyncio.run(entity.async_set_temperature(temperature=target))
    device.write_attribute.assert_awaited_once_with(
        write_message, target, mode=DataType.REQUEST
    )


def test_reference_not_yet_read() -> None:
    """Wait for the reference source, then switch to its room setpoint."""
    coordinator = make_coordinator()
    device = coordinator.config_entry.runtime_data.client.devices["200000"]
    for message, value in (
        (indoor.InFsv2091UseThermostat1, 0),
        (indoor.InFsv2092UseThermostat2, 0),
        (indoor.InOperationModeMessage, InOperationMode.HEAT),
        (indoor.InTargetTemperature, 21.0),
        (indoor.InWaterOutletTargetTemperature, 30.0),
    ):
        device.attributes[message.MESSAGE_ID] = (
            message.parse_payload(bytes([value]))
            if issubclass(message, EnumMessage)
            else message(value=value)
        )
    entity = SamsungEhsClimate(coordinator, SUBENTRY)
    assert entity.target_temperature is None
    asyncio.run(entity.async_set_temperature(temperature=22.0))
    device.write_attribute.assert_not_awaited()
    device.attributes[16495] = indoor.DhwReferenceTemperatureMessage.parse_payload(
        b"\x00"
    )
    assert entity.target_temperature == 21.0
    asyncio.run(entity.async_set_temperature(temperature=22.0))
    device.write_attribute.assert_awaited_once_with(
        indoor.InTargetTemperature, 22.0, mode=DataType.REQUEST
    )


@pytest.mark.parametrize(
    ("missing_message", "known_message"),
    [
        (indoor.InFsv2091UseThermostat1, indoor.InFsv2092UseThermostat2),
        (indoor.InFsv2092UseThermostat2, indoor.InFsv2091UseThermostat1),
    ],
)
@pytest.mark.parametrize("null_value", [False, True])
@pytest.mark.parametrize("operation", [InOperationMode.HEAT, InOperationMode.AUTO])
def test_thermostat_settings_required_before_overrides(
    *,
    missing_message: type[EnumMessage],
    known_message: type[EnumMessage],
    null_value: bool,
    operation: InOperationMode | None,
) -> None:
    """Wait for both settings even when Auto or the other input requests WL."""
    coordinator = make_coordinator()
    device = coordinator.config_entry.runtime_data.client.devices["200000"]
    device.attributes[known_message.MESSAGE_ID] = known_message.parse_payload(b"\x01")
    device.attributes[16385] = indoor.InOperationModeMessage(value=operation)
    device.attributes[16968] = indoor.InWaterLawTargetTemperature(value=2.0)
    if null_value:
        device.attributes[missing_message.MESSAGE_ID] = missing_message(value=None)
    entity = SamsungEhsClimate(coordinator, SUBENTRY)
    assert entity.current_temperature is None
    assert entity.target_temperature is None
    asyncio.run(entity.async_set_temperature(temperature=3.0))
    device.write_attribute.assert_not_awaited()
    device.attributes[missing_message.MESSAGE_ID] = missing_message.parse_payload(
        b"\x00"
    )
    assert entity.target_temperature == 2.0
    asyncio.run(entity.async_set_temperature(temperature=3.0))
    device.write_attribute.assert_awaited_once_with(
        indoor.InWaterLawTargetTemperature, 3.0, mode=DataType.REQUEST
    )


@pytest.mark.parametrize(
    ("thermostat", "operation", "expected"),
    [
        (0, None, None),
        (0, InOperationMode.FAN, None),
        (0, InOperationMode.HEAT, None),
        (0, InOperationMode.COOL, None),
        (0, InOperationMode.AUTO, 2.0),
        (1, None, 2.0),
        (1, InOperationMode.FAN, 2.0),
    ],
)
@pytest.mark.parametrize("null_reference", [False, True])
def test_operation_and_reference_requirements(
    *,
    thermostat: int,
    operation: InOperationMode | None,
    expected: float | None,
    null_reference: bool,
) -> None:
    """Require a reference only for direct Heat/Cool temperature control."""
    coordinator = make_coordinator()
    device = coordinator.config_entry.runtime_data.client.devices["200000"]
    device.attributes[16533] = indoor.InFsv2091UseThermostat1.parse_payload(
        bytes([thermostat])
    )
    device.attributes[16534] = indoor.InFsv2092UseThermostat2.parse_payload(b"\x00")
    device.attributes[16968] = indoor.InWaterLawTargetTemperature(value=2.0)
    if operation is not None:
        device.attributes[16385] = indoor.InOperationModeMessage(value=operation)
    if null_reference:
        device.attributes[16495] = indoor.DhwReferenceTemperatureMessage(value=None)
    entity = SamsungEhsClimate(coordinator, SUBENTRY)
    assert entity.target_temperature == expected
    asyncio.run(entity.async_set_temperature(temperature=3.0))
    if expected is None:
        device.write_attribute.assert_not_awaited()
    else:
        device.write_attribute.assert_awaited_once_with(
            indoor.InWaterLawTargetTemperature, 3.0, mode=DataType.REQUEST
        )


@pytest.mark.parametrize(
    ("key", "message_id", "payload", "expected"),
    [
        ("fsv2011_outdoor_temp_heating_max", 16980, b"\xff\x9c", -10.0),
        ("fsv2012_outdoor_temp_heating_min", 16981, b"\x00\x96", 15.0),
        ("fsv2031_water_out_temp_wl2_heating_max", 16984, b"\x01\xf4", 50.0),
        ("fsv2032_water_out_temp_wl2_heating_min", 16985, b"\x01^", 35.0),
    ],
)
def test_water_law_numbers(
    key: str, message_id: int, payload: bytes, expected: float
) -> None:
    """Read temperatures and write settings before unsolicited discovery."""
    coordinator = make_coordinator()
    runtime = coordinator.config_entry.runtime_data
    device = runtime.client.devices["200000"]
    description = next(item for item in NUMBERS if item.key == key)
    entity = SamsungEHSNumber(coordinator, description, SUBENTRY)
    assert entity.native_value is None
    assert runtime.messages_to_read == {"200000": [message_id]}
    device.attributes[message_id] = description.message.parse_payload(payload)
    assert entity.native_value == expected
    asyncio.run(entity.async_set_native_value(expected))
    message = device.write_attribute.call_args.args[0]
    assert message_id == message.MESSAGE_ID
    assert device.write_attribute.call_args.kwargs == {"value": expected}


@pytest.mark.parametrize(
    ("key", "message_id", "raw_value", "label"),
    [
        ("temperature_reference", 16495, 0, "room"),
        ("temperature_reference", 16495, 1, "water out"),
        ("water_law_type_heating", 16531, 1, "floor"),
        ("water_law_type_heating", 16531, 2, "fcu"),
        ("use_thermostat_zone_1", 16533, 0, "not used"),
        ("use_thermostat_zone_1", 16533, 1, "thermostat only"),
        ("remote_controller_room_temp_control", 16679, 1, "room temp only"),
        ("remote_controller_room_temp_control", 16679, 2, "wl interlink pump1"),
        ("remote_controller_room_temp_control", 16679, 3, "wl interlink pump2"),
        ("remote_controller_room_temp_control", 16679, 4, "wl interlink pump3"),
    ],
)
def test_select_enum_values(
    key: str, message_id: int, raw_value: int, label: str
) -> None:
    """Round trip one-based and zero-based enums without index arithmetic."""
    coordinator = make_coordinator()
    device = coordinator.config_entry.runtime_data.client.devices["200000"]
    description = next(item for item in SELECTS if item.key == key)
    entity = SamsungEHSSelect(coordinator, description, SUBENTRY)
    assert entity.current_option is None
    device.attributes[description.message.MESSAGE_ID] = (
        description.message.parse_payload(bytes([raw_value]))
    )
    assert entity.current_option == label
    asyncio.run(entity.async_select_option(label))
    message = device.write_attribute.call_args.args[0]
    value = device.write_attribute.call_args.kwargs["value"]
    assert message_id == message.MESSAGE_ID
    assert message.to_bytes(value) == bytes([raw_value])
