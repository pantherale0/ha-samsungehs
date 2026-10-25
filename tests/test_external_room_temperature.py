"""Exercise external room temperature action validation and notifications."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import probatio as vol
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pysamsungnasa.protocol.enum import DataType
from pysamsungnasa.protocol.factory.messages import indoor

from custom_components.samsungehs.services import (
    EXTERNAL_ROOM_TEMPERATURE_SCHEMA,
    async_register_services,
    async_set_external_room_temperature_service,
)


def make_call(**data: object) -> tuple[ServiceCall, AsyncMock]:
    """Create a service call with a connection and no discovered devices."""
    send = AsyncMock()
    entry = SimpleNamespace(
        domain="samsungehs",
        state=ConfigEntryState.LOADED,
        runtime_data=SimpleNamespace(
            client=SimpleNamespace(
                send_message=send,
                client=SimpleNamespace(is_connected=True),
            )
        ),
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: entry if entry_id == "connection" else None
        )
    )
    return ServiceCall(
        hass,
        "samsungehs",
        "set_external_room_temperature",
        {"config_entry_id": "connection", **data},
    ), send


@pytest.mark.parametrize(
    ("zone", "flag", "temperature_message"),
    [
        (1, indoor.InRoomTempSensorMessage, indoor.InRoomTempZone1Message),
        (2, indoor.InRoomTempSensorZone2Message, indoor.InRoomTempZone2Message),
    ],
)
@pytest.mark.parametrize("enabled", [True, False])
def test_notifications(
    zone: int, flag: type, temperature_message: type, *, enabled: bool
) -> None:
    """Enable with a reading, or disable without publishing a temperature."""
    call, send = make_call(zone=zone, enabled=enabled, temperature=21.4)
    asyncio.run(async_set_external_room_temperature_service(call))
    kwargs = send.await_args.kwargs
    assert kwargs["destination"] == "B0FF20"
    assert kwargs["source"] == "510000"
    assert kwargs["request_type"] == DataType.NOTIFICATION
    assert [
        (message.MESSAGE_ID, message.PAYLOAD) for message in kwargs["messages"]
    ] == (
        [(flag.MESSAGE_ID, b"\x01"), (temperature_message.MESSAGE_ID, b"\x00\xd6")]
        if enabled
        else [(flag.MESSAGE_ID, b"\x00")]
    )
    send.assert_awaited_once()


def test_disable_without_temperature() -> None:
    """Disabling does not need a reading."""
    call, send = make_call(zone=1, enabled=False)
    asyncio.run(async_set_external_room_temperature_service(call))
    messages = send.await_args.kwargs["messages"]
    assert [(message.MESSAGE_ID, message.PAYLOAD) for message in messages] == [
        (0x4076, b"\x00")
    ]


def test_enable_requires_temperature() -> None:
    """Missing readings fail before sending anything."""
    call, send = make_call(zone=1, enabled=True)
    with pytest.raises(ServiceValidationError):
        asyncio.run(async_set_external_room_temperature_service(call))
    send.assert_not_called()


@pytest.mark.parametrize("error", [ConnectionError, TimeoutError])
def test_transport_failure(error: type[OSError]) -> None:
    """Transport failures become translated Home Assistant errors."""
    call, send = make_call(zone=1, enabled=True, temperature=21.4)
    send.side_effect = error
    with pytest.raises(HomeAssistantError) as exc:
        asyncio.run(async_set_external_room_temperature_service(call))
    assert exc.value.translation_key == "external_temperature_failed"


@pytest.mark.parametrize(
    "temperature",
    [float("nan"), float("inf"), -float("inf"), True, "bad", 3276.8, -3276.9],
)
def test_invalid_temperature(temperature: object) -> None:
    """Invalid readings cannot reach the service handler."""
    with pytest.raises(vol.Invalid):
        vol.Schema(EXTERNAL_ROOM_TEMPERATURE_SCHEMA)(
            {
                "config_entry_id": "connection",
                "zone": 1,
                "enabled": True,
                "temperature": temperature,
            }
        )


@pytest.mark.parametrize("zone", [0, 3, 1.5, True, "bad"])
def test_invalid_zone(zone: object) -> None:
    """Reject unsupported zones without truncating fractional values."""
    with pytest.raises(vol.Invalid):
        vol.Schema(EXTERNAL_ROOM_TEMPERATURE_SCHEMA)(
            {"config_entry_id": "connection", "zone": zone, "enabled": False}
        )


def test_selector_input() -> None:
    """The select selector supplies zone strings."""
    assert vol.Schema(EXTERNAL_ROOM_TEMPERATURE_SCHEMA)(
        {
            "config_entry_id": "connection",
            "zone": "2",
            "enabled": True,
            "temperature": 21.4,
        }
    ) == {
        "config_entry_id": "connection",
        "zone": 2,
        "enabled": True,
        "temperature": 21.4,
    }


def test_action_registered_without_loaded_entry(tmp_path: Path) -> None:
    """The action and validation exist before any device is loaded."""

    async def exercise() -> None:
        hass = HomeAssistant(str(tmp_path))
        async_register_services(hass)
        assert hass.services.has_service("samsungehs", "set_external_room_temperature")
        with pytest.raises(vol.Invalid):
            await hass.services.async_call(
                "samsungehs",
                "set_external_room_temperature",
                {"config_entry_id": "connection", "zone": 3, "enabled": False},
                blocking=True,
            )
        await hass.async_stop()

    asyncio.run(exercise())


def test_disconnected_device() -> None:
    """Do not report success when the library would silently skip the send."""
    call, send = make_call(zone=1, enabled=False)
    entry = call.hass.config_entries.async_get_entry("connection")
    entry.runtime_data.client.client.is_connected = False
    with pytest.raises(HomeAssistantError):
        asyncio.run(async_set_external_room_temperature_service(call))
    send.assert_not_called()


@pytest.mark.parametrize(
    "state", [ConfigEntryState.NOT_LOADED, ConfigEntryState.LOADED]
)
def test_invalid_connection(state: ConfigEntryState) -> None:
    """Reject unloaded and foreign connections before sending."""
    call, send = make_call(zone=1, enabled=False)
    entry = call.hass.config_entries.async_get_entry("connection")
    entry.state = state
    if state == ConfigEntryState.LOADED:
        entry.domain = "other"
    entry.title = "Connection"
    with pytest.raises(ServiceValidationError):
        asyncio.run(async_set_external_room_temperature_service(call))
    send.assert_not_called()


def test_missing_connection() -> None:
    """A removed connection cannot fall back to another bus."""
    call, send = make_call(config_entry_id="missing", zone=1, enabled=False)
    with pytest.raises(ServiceValidationError):
        asyncio.run(async_set_external_room_temperature_service(call))
    send.assert_not_called()
