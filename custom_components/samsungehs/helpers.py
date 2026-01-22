"""Samsung EHS helper functions."""

from typing import Any

from pysamsungnasa.device import NasaDevice
from pysamsungnasa.protocol.enum import DataType, InOperationMode, SamsungEnum
from pysamsungnasa.protocol.factory.messages.indoor import (
    InFsv2091UseThermostat1,
    InFsv2092UseThermostat2,
    InOperationModeMessage,
    InTargetTemperature,
    InWaterLawTargetTemperature,
    InWaterOutletTargetTemperature,
)
from pysamsungnasa.protocol.factory.types import BaseMessage


def get_temperature_control_mode(device: NasaDevice) -> str | None:
    """
    Return the temperature control mode of the device.

    Modes: target water temperature, target room temperature, water law offset.
    """
    # Check required attributes are present in device
    required_messages = [
        InOperationModeMessage.MESSAGE_ID,
        InFsv2091UseThermostat1.MESSAGE_ID,
        InFsv2092UseThermostat2.MESSAGE_ID,
    ]
    if not all(msg in device.attributes for msg in required_messages):
        return None
    if device.attributes[InOperationModeMessage.MESSAGE_ID].VALUE in [
        InOperationMode.HEAT,
        InOperationMode.COOL,
    ]:
        return "target_water_temperature"
    if (
        device.attributes[InOperationModeMessage.MESSAGE_ID].VALUE
        == InOperationMode.AUTO
    ):
        return "water_law_offset"
    return "target_room_temperature"


async def async_set_space_heating_target_temperature(
    device: NasaDevice, temperature: float
) -> None:
    """Set target temperature for space heating mode based on the current control mode."""
    if get_temperature_control_mode(device) == "target_water_temperature":
        await device.write_attribute(
            InWaterOutletTargetTemperature, temperature, mode=DataType.REQUEST
        )
    elif get_temperature_control_mode(device) == "water_law_offset":
        await device.write_attribute(
            InWaterLawTargetTemperature, temperature, mode=DataType.REQUEST
        )
    elif get_temperature_control_mode(device) == "target_room_temperature":
        await device.write_attribute(
            InTargetTemperature, temperature, mode=DataType.REQUEST
        )
    else:
        return


def get_dict_value(
    message: BaseMessage,
    key: str,
    default: Any = None,
) -> Any:
    """Get a value from a message attribute that is a dictionary."""
    if message.VALUE is None:
        return default
    value = message.VALUE
    if not isinstance(value, dict):
        return value
    return value.get(key, default)


def convert_enum_to_select_options(enum_class: type[SamsungEnum]) -> list[str]:
    """Convert a SamsungEnum class to a list of select options."""
    return [member.name.replace("_", " ").lower() for member in enum_class]
