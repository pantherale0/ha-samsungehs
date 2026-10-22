"""Exercise FSV entity reads, writes, and polling registration."""

import unittest
from itertools import product
from types import SimpleNamespace
from unittest.mock import AsyncMock

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


class FsvEntities(unittest.IsolatedAsyncioTestCase):
    """Check values exposed to HA and values sent to the device."""

    async def test_climate_control_priority(self) -> None:
        """Use the reference source unless external thermostats or Auto select WL."""
        for thermostat1, thermostat2, reference, operation, room_control in product(
            range(5),
            range(5),
            range(2),
            (InOperationMode.HEAT, InOperationMode.COOL, InOperationMode.AUTO),
            (None, 1, 2, 3, 4),
        ):
            with self.subTest(
                thermostat1=thermostat1,
                thermostat2=thermostat2,
                reference=reference,
                operation=operation,
                room_control=room_control,
            ):
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
                    device.attributes[0x4127] = indoor.InFsv2093.parse_payload(
                        bytes([room_control])
                    )
                if thermostat1 or thermostat2 or operation == InOperationMode.AUTO:
                    current, target, write_message = (
                        2.0,
                        2.0,
                        indoor.InWaterLawTargetTemperature,
                    )
                elif reference == 0:
                    current, target, write_message = (
                        20.5,
                        21.0,
                        indoor.InTargetTemperature,
                    )
                else:
                    current, target, write_message = (
                        33.5,
                        30.0,
                        indoor.InWaterOutletTargetTemperature,
                    )
                entity = SamsungEhsClimate(coordinator, SUBENTRY)
                self.assertEqual(entity.current_temperature, current)
                self.assertEqual(entity.target_temperature, target)
                await entity.async_set_temperature(temperature=target)
                device.write_attribute.assert_awaited_once_with(
                    write_message, target, mode=DataType.REQUEST
                )

    async def test_reference_not_yet_read(self) -> None:
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
        self.assertIsNone(entity.target_temperature)
        await entity.async_set_temperature(temperature=22.0)
        device.write_attribute.assert_not_awaited()
        device.attributes[0x406F] = indoor.DhwReferenceTemperatureMessage.parse_payload(
            b"\x00"
        )
        self.assertEqual(entity.target_temperature, 21.0)
        await entity.async_set_temperature(temperature=22.0)
        device.write_attribute.assert_awaited_once_with(
            indoor.InTargetTemperature, 22.0, mode=DataType.REQUEST
        )

    async def test_thermostat_settings_required_before_overrides(self) -> None:
        """Wait for both settings even when Auto or the other input requests WL."""
        for missing_message, known_message in (
            (indoor.InFsv2091UseThermostat1, indoor.InFsv2092UseThermostat2),
            (indoor.InFsv2092UseThermostat2, indoor.InFsv2091UseThermostat1),
        ):
            for null_value, operation in product(
                (False, True), (InOperationMode.HEAT, InOperationMode.AUTO)
            ):
                with self.subTest(
                    missing=missing_message.MESSAGE_ID,
                    null_value=null_value,
                    operation=operation,
                ):
                    coordinator = make_coordinator()
                    device = coordinator.config_entry.runtime_data.client.devices[
                        "200000"
                    ]
                    device.attributes[known_message.MESSAGE_ID] = (
                        known_message.parse_payload(b"\x01")
                    )
                    device.attributes[0x4001] = indoor.InOperationModeMessage(
                        value=operation
                    )
                    device.attributes[0x4248] = indoor.InWaterLawTargetTemperature(
                        value=2.0
                    )
                    if null_value:
                        device.attributes[missing_message.MESSAGE_ID] = missing_message(
                            value=None
                        )
                    entity = SamsungEhsClimate(coordinator, SUBENTRY)
                    self.assertIsNone(entity.current_temperature)
                    self.assertIsNone(entity.target_temperature)
                    await entity.async_set_temperature(temperature=3.0)
                    device.write_attribute.assert_not_awaited()
                    device.attributes[missing_message.MESSAGE_ID] = (
                        missing_message.parse_payload(b"\x00")
                    )
                    self.assertEqual(entity.target_temperature, 2.0)
                    await entity.async_set_temperature(temperature=3.0)
                    device.write_attribute.assert_awaited_once_with(
                        indoor.InWaterLawTargetTemperature, 3.0, mode=DataType.REQUEST
                    )

    async def test_operation_and_reference_requirements(self) -> None:
        """Require a reference only for direct Heat/Cool temperature control."""
        cases = (
            (0, None, None),
            (0, InOperationMode.FAN, None),
            (0, InOperationMode.HEAT, None),
            (0, InOperationMode.COOL, None),
            (0, InOperationMode.AUTO, 2.0),
            (1, None, 2.0),
            (1, InOperationMode.FAN, 2.0),
        )
        for thermostat, operation, expected in cases:
            for null_reference in (False, True):
                with self.subTest(
                    thermostat=thermostat,
                    operation=operation,
                    null_reference=null_reference,
                ):
                    coordinator = make_coordinator()
                    device = coordinator.config_entry.runtime_data.client.devices[
                        "200000"
                    ]
                    device.attributes[0x4095] = (
                        indoor.InFsv2091UseThermostat1.parse_payload(
                            bytes([thermostat])
                        )
                    )
                    device.attributes[0x4096] = (
                        indoor.InFsv2092UseThermostat2.parse_payload(b"\x00")
                    )
                    device.attributes[0x4248] = indoor.InWaterLawTargetTemperature(
                        value=2.0
                    )
                    if operation is not None:
                        device.attributes[0x4001] = indoor.InOperationModeMessage(
                            value=operation
                        )
                    if null_reference:
                        device.attributes[0x406F] = (
                            indoor.DhwReferenceTemperatureMessage(value=None)
                        )
                    entity = SamsungEhsClimate(coordinator, SUBENTRY)
                    self.assertEqual(entity.target_temperature, expected)
                    await entity.async_set_temperature(temperature=3.0)
                    if expected is None:
                        device.write_attribute.assert_not_awaited()
                    else:
                        device.write_attribute.assert_awaited_once_with(
                            indoor.InWaterLawTargetTemperature,
                            3.0,
                            mode=DataType.REQUEST,
                        )

    async def test_water_law_numbers(self) -> None:
        """Read temperatures and write settings before unsolicited discovery."""
        cases = (
            ("fsv2011_outdoor_temp_heating_max", 0x4254, b"\xff\x9c", -10.0),
            ("fsv2012_outdoor_temp_heating_min", 0x4255, b"\x00\x96", 15.0),
            ("fsv2031_water_out_temp_wl2_heating_max", 0x4258, b"\x01\xf4", 50.0),
            ("fsv2032_water_out_temp_wl2_heating_min", 0x4259, b"\x01\x5e", 35.0),
        )
        for key, message_id, payload, expected in cases:
            with self.subTest(key=key):
                coordinator = make_coordinator()
                runtime = coordinator.config_entry.runtime_data
                device = runtime.client.devices["200000"]
                description = next(item for item in NUMBERS if item.key == key)
                entity = SamsungEHSNumber(coordinator, description, SUBENTRY)
                self.assertIsNone(entity.native_value)
                self.assertEqual(runtime.messages_to_read, {"200000": [message_id]})
                device.attributes[message_id] = description.message.parse_payload(
                    payload
                )
                self.assertEqual(entity.native_value, expected)
                await entity.async_set_native_value(expected)
                message = device.write_attribute.call_args.args[0]
                self.assertEqual(message.MESSAGE_ID, message_id)
                self.assertEqual(
                    device.write_attribute.call_args.kwargs, {"value": expected}
                )

    async def test_select_enum_values(self) -> None:
        """Round trip one-based and zero-based enums without index arithmetic."""
        cases = (
            ("temperature_reference", 0x406F, 0, "room"),
            ("temperature_reference", 0x406F, 1, "water out"),
            ("water_law_type_heating", 0x4093, 1, "floor"),
            ("water_law_type_heating", 0x4093, 2, "fcu"),
            ("use_thermostat_zone_1", 0x4095, 0, "not used"),
            ("use_thermostat_zone_1", 0x4095, 1, "thermostat only"),
            ("remote_controller_room_temp_control", 0x4127, 1, "room temp only"),
            ("remote_controller_room_temp_control", 0x4127, 2, "wl interlink pump1"),
            ("remote_controller_room_temp_control", 0x4127, 3, "wl interlink pump2"),
            ("remote_controller_room_temp_control", 0x4127, 4, "wl interlink pump3"),
        )
        for key, message_id, raw_value, label in cases:
            with self.subTest(key=key, value=raw_value):
                coordinator = make_coordinator()
                device = coordinator.config_entry.runtime_data.client.devices["200000"]
                description = next(item for item in SELECTS if item.key == key)
                entity = SamsungEHSSelect(coordinator, description, SUBENTRY)
                self.assertIsNone(entity.current_option)
                device.attributes[description.message.MESSAGE_ID] = (
                    description.message.parse_payload(bytes([raw_value]))
                )
                self.assertEqual(entity.current_option, label)
                await entity.async_select_option(label)
                message = device.write_attribute.call_args.args[0]
                value = device.write_attribute.call_args.kwargs["value"]
                self.assertEqual(message.MESSAGE_ID, message_id)
                self.assertEqual(message.to_bytes(value), bytes([raw_value]))
