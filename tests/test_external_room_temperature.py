"""External readings are validated and routed by the real HA service dispatcher."""

from unittest.mock import MagicMock

import probatio as vol
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.setup import async_setup_component
from pysamsungnasa.protocol.enum import DataType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import DOMAIN


async def test_registered_before_entry(hass: HomeAssistant) -> None:
    """Integration actions register without any loaded device."""
    assert await async_setup_component(hass, DOMAIN, {})
    for action in (
        "set_external_room_temperature",
        "read_attribute",
        "write_attribute",
    ):
        assert hass.services.has_service(DOMAIN, action)


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize(
    ("zone", "flag", "temperature_id"), [(1, 0x4076, 0x423A), (2, 0x4118, 0x42DA)]
)
@pytest.mark.parametrize(
    ("enabled", "temperature", "payload"),
    [
        (True, 21.4, b"\x00\xd6"),
        (True, -10.0, b"\xff\x9c"),
        (True, -3276.8, b"\x80\x00"),
        (True, 3276.7, b"\x7f\xff"),
        (False, None, None),
    ],
)
async def test_notification(
    hass: HomeAssistant,
    mock_nasa: MagicMock,
    zone: int,
    flag: int,
    temperature_id: int,
    *,
    enabled: bool,
    temperature: float | None,
    payload: bytes | None,
) -> None:
    """Both zones use literal notification destinations, IDs and signed bytes."""
    data = {"config_entry_id": "connection", "zone": str(zone), "enabled": enabled}
    if temperature is not None:
        data["temperature"] = temperature
    await hass.services.async_call(
        DOMAIN, "set_external_room_temperature", data, blocking=True
    )
    send = mock_nasa.return_value.send_message
    send.assert_awaited_once()
    args = send.await_args.kwargs
    assert args["destination"] == "B0FF20"
    assert args["source"] == "510000"
    assert args["request_type"] == DataType.NOTIFICATION
    expected = (
        [(flag, b"\x01"), (temperature_id, payload)] if enabled else [(flag, b"\x00")]
    )
    assert [(m.MESSAGE_ID, m.PAYLOAD) for m in args["messages"]] == expected


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize(
    "temperature",
    [float("nan"), float("inf"), -float("inf"), True, "bad", 3276.8, -3276.9],
)
async def test_invalid_temperature(
    hass: HomeAssistant, mock_nasa: MagicMock, temperature: object
) -> None:
    """Invalid readings fail at service validation without sending anything."""
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "set_external_room_temperature",
            {
                "config_entry_id": "connection",
                "zone": 1,
                "enabled": True,
                "temperature": temperature,
            },
            blocking=True,
        )
    mock_nasa.return_value.send_message.assert_not_awaited()


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize("zone", [0, 3, 1.5, True, "bad"])
async def test_invalid_zone(
    hass: HomeAssistant, mock_nasa: MagicMock, zone: object
) -> None:
    """Fractional and unsupported zones never reach the library."""
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "set_external_room_temperature",
            {"config_entry_id": "connection", "zone": zone, "enabled": False},
            blocking=True,
        )
    mock_nasa.return_value.send_message.assert_not_awaited()


@pytest.mark.usefixtures("integration")
async def test_missing_reading(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """Enabling a sensor requires a temperature and reports a translated error."""
    with pytest.raises(ServiceValidationError) as exc:
        await hass.services.async_call(
            DOMAIN,
            "set_external_room_temperature",
            {"config_entry_id": "connection", "zone": 1, "enabled": True},
            blocking=True,
        )
    assert exc.value.translation_key == "external_temperature_required"
    mock_nasa.return_value.send_message.assert_not_awaited()


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize("error", [ConnectionError, TimeoutError])
async def test_transport_failure(
    hass: HomeAssistant, mock_nasa: MagicMock, error: type[OSError]
) -> None:
    """Transport errors become translated Home Assistant errors."""
    mock_nasa.return_value.send_message.side_effect = error
    with pytest.raises(HomeAssistantError) as exc:
        await hass.services.async_call(
            DOMAIN,
            "set_external_room_temperature",
            {"config_entry_id": "connection", "zone": 1, "enabled": False},
            blocking=True,
        )
    assert exc.value.translation_key == "external_temperature_failed"


@pytest.mark.usefixtures("integration")
async def test_disconnected(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """A disconnected client cannot report a successful broadcast."""
    mock_nasa.return_value.client._is_connected = False
    with pytest.raises(HomeAssistantError) as exc:
        await hass.services.async_call(
            DOMAIN,
            "set_external_room_temperature",
            {"config_entry_id": "connection", "zone": 1, "enabled": False},
            blocking=True,
        )
    assert exc.value.translation_key == "external_temperature_failed"
    mock_nasa.return_value.send_message.assert_not_awaited()


@pytest.mark.usefixtures("integration")
@pytest.mark.parametrize("target", ["missing", "unloaded", "foreign"])
async def test_bad_connection(
    hass: HomeAssistant, mock_nasa: MagicMock, target: str
) -> None:
    """Missing, unloaded and foreign connections cannot fall back to another bus."""
    if target != "missing":
        MockConfigEntry(
            domain="other" if target == "foreign" else DOMAIN,
            entry_id=target,
            version=2,
        ).add_to_hass(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "set_external_room_temperature",
            {"config_entry_id": target, "zone": 1, "enabled": False},
            blocking=True,
        )
    mock_nasa.return_value.send_message.assert_not_awaited()
