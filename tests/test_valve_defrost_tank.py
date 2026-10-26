"""Check the 3-way valve, defrost, DHW tank and thermo on entities."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from pysamsungnasa.protocol.enum import (
    OutdoorIndoorDefrostStep,
    OutdoorOperationStatus,
)
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
from custom_components.samsungehs.sensor import (
    OUTDOOR_ENTITY_DESCRIPTIONS as OUTDOOR_SENSORS,
)
from custom_components.samsungehs.sensor import SamsungEhsSensor, SamsungEhsSensorKey

COMPONENT = Path(__file__).parents[1] / "custom_components" / "samsungehs"


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


@pytest.mark.parametrize(
    ("key", "message", "payload", "state"),
    [
        (
            "operation_status",
            outdoor.OutdoorOperationStatusMessage,
            bytes([OutdoorOperationStatus.OP_NORMAL]),
            "op_normal",
        ),
        (
            "defrost_status",
            outdoor.OutdoorDefrostStatus,
            bytes([OutdoorIndoorDefrostStep.NO_DEFROST_OPERATION]),
            "no_defrost_operation",
        ),
    ],
)
def test_outdoor_enum_sensors(
    key: str, message: type, payload: bytes, state: str
) -> None:
    """Enum sensors expose lower-case states supported by their options."""
    sensor, device = entity(SamsungEhsSensor, OUTDOOR_SENSORS, key, "100000")
    assert sensor.native_value is None
    device.attributes[message.MESSAGE_ID] = message.parse_payload(payload)

    assert sensor.native_value == state
    assert state in sensor.entity_description.options
    assert sensor.entity_description.entity_category == EntityCategory.DIAGNOSTIC


def test_requested_sensor_descriptions() -> None:
    """Requested diagnostics use their broadcast messages and correct units."""
    expected = {
        SamsungEhsSensorKey.OPERATION_STATUS: (0x8001, None, None),
        SamsungEhsSensorKey.DEFROST_STATUS: (0x8061, None, None),
        SamsungEhsSensorKey.DEFROST_STAGE: (0x8247, None, SensorStateClass.MEASUREMENT),
        SamsungEhsSensorKey.DISCHARGE_TEMPERATURE: (
            0x8280,
            UnitOfTemperature.CELSIUS,
            SensorStateClass.MEASUREMENT,
        ),
        SamsungEhsSensorKey.OUTDOOR_CURRENT: (
            0x8217,
            UnitOfElectricCurrent.AMPERE,
            SensorStateClass.MEASUREMENT,
        ),
        SamsungEhsSensorKey.SUPPLY_VOLTAGE: (
            0x24FC,
            UnitOfElectricPotential.VOLT,
            SensorStateClass.MEASUREMENT,
        ),
    }
    descriptions = {description.key: description for description in OUTDOOR_SENSORS}

    for key, (message_id, unit, state_class) in expected.items():
        description = descriptions[key]
        assert message_id == description.message.MESSAGE_ID
        assert description.native_unit_of_measurement == unit
        assert description.state_class == state_class
        assert description.entity_category == EntityCategory.DIAGNOSTIC
        assert not description.requires_read

    indoor_expected = {
        SamsungEhsSensorKey.CAPACITY_REQUEST: (0x4211, None),
        SamsungEhsSensorKey.ROOM_TEMPERATURE: (0x4203, UnitOfTemperature.CELSIUS),
        SamsungEhsSensorKey.ROOM_TARGET_TEMPERATURE: (
            0x4201,
            UnitOfTemperature.CELSIUS,
        ),
        SamsungEhsSensorKey.DHW_TARGET_TEMPERATURE: (
            0x4235,
            UnitOfTemperature.CELSIUS,
        ),
    }
    indoor_descriptions = {
        description.key: description for description in INDOOR_SENSORS
    }
    for key, (message_id, unit) in indoor_expected.items():
        description = indoor_descriptions[key]
        assert message_id == description.message.MESSAGE_ID
        assert description.native_unit_of_measurement == unit
        assert description.entity_category == EntityCategory.DIAGNOSTIC
        assert not description.requires_read


@pytest.mark.parametrize("file_name", ["strings.json", "translations/en.json"])
def test_diagnostic_entity_translations(file_name: str) -> None:
    """All new sensors and the valve binary sensor have translated names/states."""
    translations = json.loads((COMPONENT / file_name).read_text(encoding="utf-8"))[
        "entity"
    ]
    sensor_translations = translations["sensor"]
    binary_translations = translations["binary_sensor"]

    expected_names = {
        "operation_status": "Operation Status",
        "defrost_status": "Defrost Status",
        "defrost_stage": "Defrost Stage",
        "discharge_temperature": "Discharge Temperature",
        "outdoor_current": "Outdoor Current",
        "supply_voltage": "Supply Voltage",
        "capacity_request": "Capacity Request",
        "room_temperature": "Room Temperature",
        "room_target_temperature": "Room Target Temperature",
        "dhw_target_temperature": "DHW Target Temperature",
    }
    for key, name in expected_names.items():
        assert sensor_translations[key]["name"] == name

    for key in ("operation_status", "defrost_status"):
        description = next(item for item in OUTDOOR_SENSORS if item.key == key)
        assert set(description.options) == set(sensor_translations[key]["state"])

    assert binary_translations["four_way_valve"]["name"] == "4-Way Valve"


def test_defrost_stage_sensor_value() -> None:
    """Defrost stage is exposed as the numeric value from message 0x8247."""
    sensor, device = entity(
        SamsungEhsSensor, OUTDOOR_SENSORS, "defrost_stage", "100000"
    )
    device.attributes[0x8247] = outdoor.OutdoorDefrostStage.parse_payload(b"\x00")
    assert sensor.native_value == 0.0


@pytest.mark.parametrize(("raw", "on"), [(1, True), (0, False)])
def test_four_way_valve(raw: int, on: bool) -> None:  # noqa: FBT001
    """The four-way valve binary sensor maps 0x801A on/off."""
    sensor, device = entity(
        SamsungEhsBinarySensor, OUTDOOR_BINARY, "four_way_valve", "100000"
    )
    device.attributes[0x801A] = outdoor.OutdoorLoad4WayValveMessage.parse_payload(
        bytes([raw])
    )
    assert sensor.is_on is on
    assert sensor.entity_description.entity_category == EntityCategory.DIAGNOSTIC
    assert not sensor.entity_description.requires_read


@pytest.mark.parametrize(("raw", "on"), [(1, True), (0, False)])
def test_thermo_on(raw: int, on: bool) -> None:  # noqa: FBT001
    """Thermo on reads 0x4028."""
    sensor, device = entity(
        SamsungEhsBinarySensor, INDOOR_BINARY, "indoor_thermo_on", "200000"
    )
    device.attributes[0x4028] = indoor.InStateThermo.parse_payload(bytes([raw]))
    assert sensor.is_on is on
