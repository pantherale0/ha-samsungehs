"""Small literal tables cover the pure control-source decisions."""

from unittest.mock import MagicMock

import pytest
from pysamsungnasa.device import NasaDevice
from pysamsungnasa.protocol.factory.messages import MESSAGE_PARSERS
from pysamsungnasa.protocol.factory.messages.indoor import InTargetTemperature

from custom_components.samsungehs.helpers import (
    get_dict_value,
    get_temperature_control_mode,
)


@pytest.mark.parametrize(
    ("thermostat1", "thermostat2", "operation", "reference", "expected"),
    [
        (None, 1, 0, 0, None),
        (1, None, 0, 0, None),
        (0, 0, None, 0, None),
        (0, 0, 3, 0, None),
        (0, 0, 4, None, None),
        (0, 0, 1, None, None),
        (0, 0, 4, 0, "target_room_temperature"),
        (0, 0, 1, 1, "target_water_temperature"),
        (0, 0, 0, None, "water_law_offset"),
        (1, 0, None, None, "water_law_offset"),
        (0, 1, 3, None, "water_law_offset"),
        (4, 0, 4, 0, "water_law_offset"),
        (0, 4, 1, 1, "water_law_offset"),
    ],
)
def test_control_priority(
    thermostat1: int | None,
    thermostat2: int | None,
    operation: int | None,
    reference: int | None,
    expected: str | None,
) -> None:
    """Unknown inputs, explicit sources and overrides have distinct expectations."""
    device = MagicMock(spec=NasaDevice)
    device.attributes = {}
    for message_id, value in [
        (0x4095, thermostat1),
        (0x4096, thermostat2),
        (0x4001, operation),
        (0x406F, reference),
    ]:
        if value is not None:
            device.attributes[message_id] = MESSAGE_PARSERS[message_id].parse_payload(
                bytes([value])
            )
    assert get_temperature_control_mode(device) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, "fallback"), (1, 1), ({"key": 2}, 2), ({}, "fallback")],
)
def test_dict_value(value: object, expected: object) -> None:
    """Dictionary reads preserve scalar values and handle absent fields."""
    assert (
        get_dict_value(InTargetTemperature(value=value), "key", "fallback") == expected
    )
