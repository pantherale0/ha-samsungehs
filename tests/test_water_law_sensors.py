"""Check the water law target and offset sensors read the right messages."""

import json
from pathlib import Path

import pytest
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.samsungehs.sensor import (
    INDOOR_ENTITY_DESCRIPTIONS,
    SamsungEhsSensorKey,
)

COMPONENT = Path(__file__).parents[1] / "custom_components" / "samsungehs"


@pytest.mark.parametrize(
    ("key", "message_id", "device_class"),
    [
        (
            SamsungEhsSensorKey.WATER_LAW_TARGET_TEMPERATURE,
            0x427F,
            SensorDeviceClass.TEMPERATURE,
        ),
        (
            SamsungEhsSensorKey.WATER_LAW_OFFSET,
            0x4248,
            SensorDeviceClass.TEMPERATURE_DELTA,
        ),
    ],
)
def test_water_law_sensor_messages(
    key: str, message_id: int, device_class: SensorDeviceClass
) -> None:
    """The target follows the curve (0x427F); the offset is its shift (0x4248)."""
    # The offset is a difference: 2 °C must show as 3.6 °F, not 35.6 °F.
    description = next(d for d in INDOOR_ENTITY_DESCRIPTIONS if d.key == key)

    assert message_id == description.message.MESSAGE_ID
    assert description.device_class == device_class


@pytest.mark.parametrize("file_name", ["strings.json", "translations/en.json"])
def test_water_law_offset_name(file_name: str) -> None:
    """The offset sensor has a display name."""
    strings = json.loads((COMPONENT / file_name).read_text(encoding="utf-8"))

    assert (
        strings["entity"]["sensor"][SamsungEhsSensorKey.WATER_LAW_OFFSET]["name"]
        == "Water Law Offset"
    )
