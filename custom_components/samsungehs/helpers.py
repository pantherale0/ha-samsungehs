"""Samsung EHS helper functions."""

from typing import Any

from pysamsungnasa.device import NasaDevice
from pysamsungnasa.protocol.enum import (
    DataType,
    DhwReferenceTemp,
    InOperationMode,
    InUseThermostat,
    SamsungEnum,
)
from pysamsungnasa.protocol.factory.messages.indoor import (
    DhwReferenceTemperatureMessage,
    InFsv2091UseThermostat1,
    InFsv2092UseThermostat2,
    InOperationModeMessage,
    InTargetTemperature,
    InWaterLawOffsetTemperature,
    InWaterOutletTargetTemperature,
)
from pysamsungnasa.protocol.factory.types import BaseMessage


def get_temperature_control_mode(device: NasaDevice) -> str | None:
    """
    Return the temperature control mode of the device.

    Modes: target water temperature, target room temperature, water law offset.
    """
    thermostat_settings = [
        device.attributes.get(message.MESSAGE_ID)
        for message in (InFsv2091UseThermostat1, InFsv2092UseThermostat2)
    ]
    operation = device.attributes.get(InOperationModeMessage.MESSAGE_ID)
    reference = device.attributes.get(DhwReferenceTemperatureMessage.MESSAGE_ID)

    if any(setting is None or setting.VALUE is None for setting in thermostat_settings):
        return None

    if any(
        setting.VALUE is not InUseThermostat.NOT_USED for setting in thermostat_settings
    ) or (operation is not None and operation.VALUE == InOperationMode.AUTO):
        return "water_law_offset"

    if operation is None or operation.VALUE not in (
        InOperationMode.HEAT,
        InOperationMode.COOL,
    ):
        return None

    if reference is None:
        return None

    return {
        DhwReferenceTemp.ROOM: "target_room_temperature",
        DhwReferenceTemp.WATER_OUT: "target_water_temperature",
    }.get(reference.VALUE)


async def async_set_space_heating_target_temperature(
    device: NasaDevice, temperature: float
) -> None:
    """Set the space heating target using the configured temperature control."""
    if get_temperature_control_mode(device) == "target_water_temperature":
        await device.write_attribute(
            InWaterOutletTargetTemperature, temperature, mode=DataType.REQUEST
        )
    elif get_temperature_control_mode(device) == "water_law_offset":
        await device.write_attribute(
            InWaterLawOffsetTemperature, temperature, mode=DataType.REQUEST
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
