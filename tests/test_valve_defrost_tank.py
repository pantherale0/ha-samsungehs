"""Check the 3-way valve, defrost, DHW tank and thermo on entities."""

from types import SimpleNamespace
from typing import Any

import pytest
from pysamsungnasa.protocol.enum import OutdoorOperationStatus
from pysamsungnasa.protocol.factory.messages import indoor, outdoor

from custom_components.samsungehs.binary_sensor import (
    INDOOR_ENTITY_DESCRIPTIONS as INDOOR_BINARY,
)
from custom_components.samsungehs.binary_sensor import (
    OUTDOOR_ENTITY_DESCRIPTIONS as OUTDOOR_BINARY,
)
from custom_components.samsungehs.binary_sensor import (
    SamsungEhsBinarySensor,
)
from custom_components.samsungehs.sensor import (
    INDOOR_ENTITY_DESCRIPTIONS as INDOOR_SENSORS,
)
from custom_components.samsungehs.sensor import SamsungEhsSensor


def make_coordinator(address: str) -> SimpleNamespace:
    """Provide a device boundary without connecting to hardware."""
    device = SimpleNamespace(attributes={})
    runtime = SimpleNamespace(
        client=SimpleNamespace(
            devices={address: device}, client=SimpleNamespace(is_connected=True)
        ),
        messages_to_read={},
    )
    return SimpleNamespace(
        config_entry=SimpleNamespace(runtime_data=runtime), last_update_success=True
    )


def entity(
    entity_class: type, descriptions: tuple, key: str, address: str
) -> tuple[Any, SimpleNamespace]:
    """Build one entity and return it with its device attributes."""
    coordinator = make_coordinator(address)
    description = next(item for item in descriptions if item.key == key)
    subentry = SimpleNamespace(unique_id=address, subentry_id=address)
    built = entity_class(coordinator, description, subentry)
    return built, coordinator.config_entry.runtime_data.client.devices[address]


@pytest.mark.parametrize(("raw", "state"), [(0, "room"), (1, "tank")])
def test_three_way_valve(raw: int, state: str) -> None:
    """The valve reads 0x4067 as room or tank, one of the declared options."""
    sensor, device = entity(
        SamsungEhsSensor, INDOOR_SENSORS, "three_way_valve", "200000"
    )
    assert sensor.native_value is None
    device.attributes[0x4067] = indoor.In3WayValveMessage.parse_payload(bytes([raw]))
    assert sensor.native_value == state
    assert sensor.entity_description.options == ["room", "tank"]


def test_dhw_tank_temperature() -> None:
    """The tank temperature reads 0x4237 in tenths of a degree."""
    sensor, device = entity(
        SamsungEhsSensor, INDOOR_SENSORS, "dhw_tank_temperature", "200000"
    )
    device.attributes[0x4237] = indoor.DhwCurrentTemperature.parse_payload(b"\x01\x76")
    assert sensor.native_value == pytest.approx(37.4)


@pytest.mark.parametrize(
    ("status", "on"),
    [
        (OutdoorOperationStatus.OP_DEICE, True),
        (OutdoorOperationStatus.OP_NONSTOP_DEICE, True),
        (OutdoorOperationStatus.OP_NORMAL, False),
        (OutdoorOperationStatus.OP_STOP, False),
        (OutdoorOperationStatus.OP_SAFETY, False),
    ],
)
def test_defrost(status: OutdoorOperationStatus, on: bool) -> None:  # noqa: FBT001
    """Defrost follows the outdoor operation status (0x8001), as climate does."""
    sensor, device = entity(SamsungEhsBinarySensor, OUTDOOR_BINARY, "defrost", "100000")
    device.attributes[0x8001] = outdoor.OutdoorOperationStatusMessage.parse_payload(
        bytes([status])
    )
    assert sensor.is_on is on


@pytest.mark.parametrize(("raw", "on"), [(1, True), (0, False)])
def test_thermo_on(raw: int, on: bool) -> None:  # noqa: FBT001
    """Thermo on reads 0x4028."""
    sensor, device = entity(
        SamsungEhsBinarySensor, INDOOR_BINARY, "indoor_thermo_on", "200000"
    )
    device.attributes[0x4028] = indoor.InStateThermo.parse_payload(bytes([raw]))
    assert sensor.is_on is on
