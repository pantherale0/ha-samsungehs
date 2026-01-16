"""Samsung EHS helper functions."""

from pysamsungnasa.device import NasaDevice
from pysamsungnasa.protocol.enum import InOperationMode
from pysamsungnasa.protocol.factory.messages.indoor import (
    InFsv2091UseThermostat1,
    InFsv2092UseThermostat2,
    InOperationModeMessage,
    InWaterOutletTargetTemperature,
    InWaterLawTargetTemperature,
    InTargetTemperature,
)


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
    if device.attributes[InOperationModeMessage.MESSAGE_ID] in [
        InOperationMode.HEAT,
        InOperationMode.COOL,
    ]:
        return "target_water_temperature"
    if device.attributes[InOperationModeMessage.MESSAGE_ID] == InOperationMode.AUTO:
        return "water_law_offset"
    return "target_room_temperature"


async def async_set_space_heating_target_temperature(
    device: NasaDevice, temperature: float
) -> None:
    """Set target temperature for space heating mode based on the current control mode."""
    if get_temperature_control_mode(device) == "target_water_temperature":
        await device.write_attribute(InWaterOutletTargetTemperature, temperature)
    elif get_temperature_control_mode(device) == "water_law_offset":
        await device.write_attribute(InWaterLawTargetTemperature, temperature)
    elif get_temperature_control_mode(device) == "target_room_temperature":
        await device.write_attribute(InTargetTemperature, temperature)
    else:
        return
