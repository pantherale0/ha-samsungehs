"""Exercise FSV entity reads, writes, and polling registration."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.samsungehs.number import NUMBERS, SamsungEHSNumber
from custom_components.samsungehs.select import SELECTS, SamsungEHSSelect


def make_coordinator() -> SimpleNamespace:
    """Provide a device boundary without connecting to hardware."""
    device = SimpleNamespace(attributes={}, write_attribute=AsyncMock())
    runtime = SimpleNamespace(
        client=SimpleNamespace(devices={"200000": device}), messages_to_read={}
    )
    return SimpleNamespace(config_entry=SimpleNamespace(runtime_data=runtime))


SUBENTRY = SimpleNamespace(unique_id="200000", subentry_id="indoor")


class FsvEntities(unittest.IsolatedAsyncioTestCase):
    """Check values exposed to HA and values sent to the device."""

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
