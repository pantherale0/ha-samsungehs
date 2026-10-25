"""Verify reported override state and temperature availability for both zones."""

from types import SimpleNamespace

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from pysamsungnasa.protocol.factory.messages import indoor

from custom_components.samsungehs.binary_sensor import (
    INDOOR_ENTITY_DESCRIPTIONS as BINARY_DESCRIPTIONS,
)
from custom_components.samsungehs.binary_sensor import (
    SamsungEhsBinarySensor,
)
from custom_components.samsungehs.sensor import (
    INDOOR_ENTITY_DESCRIPTIONS as SENSOR_DESCRIPTIONS,
)
from custom_components.samsungehs.sensor import (
    SamsungEhsSensor,
)


def make_entities(
    zone: int,
) -> tuple[SamsungEhsSensor, SamsungEhsBinarySensor, SimpleNamespace]:
    """Use real entity classes with a device attribute cache."""
    device = SimpleNamespace(attributes={})
    runtime = SimpleNamespace(
        client=SimpleNamespace(
            devices={"200000": device}, client=SimpleNamespace(is_connected=True)
        ),
        messages_to_read={},
    )
    coordinator = SimpleNamespace(
        config_entry=SimpleNamespace(runtime_data=runtime), last_update_success=True
    )
    subentry = SimpleNamespace(unique_id="200000", subentry_id="indoor")
    sensor = SamsungEhsSensor(
        coordinator,
        next(
            d
            for d in SENSOR_DESCRIPTIONS
            if d.key == f"zone_{zone}_external_room_temperature"
        ),
        subentry,
    )
    binary = SamsungEhsBinarySensor(
        coordinator,
        next(
            d
            for d in BINARY_DESCRIPTIONS
            if d.key == f"zone_{zone}_external_room_sensor_enabled"
        ),
        subentry,
    )
    return sensor, binary, device


@pytest.mark.parametrize(
    ("zone", "flag", "temperature"),
    [
        (1, indoor.InRoomTempSensorMessage, indoor.InRoomTempZone1Message),
        (2, indoor.InRoomTempSensorZone2Message, indoor.InRoomTempZone2Message),
    ],
)
def test_reported_state_transitions(zone: int, flag: type, temperature: type) -> None:
    """Unknown, enabled, disabled, and re-enabled reports update each zone."""
    sensor, binary, device = make_entities(zone)
    assert binary.available
    assert binary.is_on is None
    assert not sensor.available
    device.attributes[temperature.MESSAGE_ID] = temperature(value=21.4)
    assert not sensor.available
    device.attributes[flag.MESSAGE_ID] = flag(value=True)
    assert binary.is_on is True
    assert sensor.available
    assert sensor.native_value == 21.4
    device.attributes[flag.MESSAGE_ID] = flag(value=False)
    assert binary.available
    assert binary.is_on is False
    assert not sensor.available
    device.attributes[flag.MESSAGE_ID] = flag(value=True)
    assert sensor.available
    assert sensor.native_value == 21.4
    device.attributes[temperature.MESSAGE_ID] = temperature(value=None)
    assert not sensor.available
    assert binary.is_on is True


@pytest.mark.parametrize("zone", [1, 2])
def test_metadata_and_polling(zone: int) -> None:
    """Both dependencies are read without depending on binary sensor activation."""
    sensor, _, _ = make_entities(zone)
    assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE
    assert sensor.state_class == SensorStateClass.MEASUREMENT
    assert set(
        sensor.coordinator.config_entry.runtime_data.messages_to_read["200000"]
    ) == ({0x4076, 0x423A} if zone == 1 else {0x4118, 0x42DA})


def test_other_zone_does_not_enable_sensor() -> None:
    """Zone 2 flags cannot enable zone 1 readings."""
    sensor, binary, device = make_entities(1)
    device.attributes[0x4118] = indoor.InRoomTempSensorZone2Message(value=True)
    device.attributes[0x423A] = indoor.InRoomTempZone1Message(value=21.4)
    assert binary.is_on is None
    assert not sensor.available


@pytest.mark.parametrize("zone", [1, 2])
def test_disconnect_and_removed_device(zone: int) -> None:
    """Losing the device or connection makes both entities unavailable."""
    sensor, binary, _ = make_entities(zone)
    runtime = sensor.coordinator.config_entry.runtime_data
    runtime.client.client.is_connected = False
    assert not sensor.available
    assert not binary.available
    assert binary.is_on is None
    runtime.client.client.is_connected = True
    runtime.client.devices.clear()
    assert not sensor.available
    assert not binary.available
