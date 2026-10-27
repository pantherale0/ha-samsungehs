"""Switch reported values and HA power actions."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from . import Report, entity_id

pytestmark = pytest.mark.usefixtures("integration")


@pytest.mark.parametrize(
    ("action", "payload", "expected"),
    [("turn_on", "01", "on"), ("turn_off", "00", "off")],
)
@pytest.mark.parametrize(
    ("key", "message_id"), [("quiet_mode", 0x4046), ("outing_mode", 0x406D)]
)
async def test_switch(
    hass: HomeAssistant,
    mock_nasa: MagicMock,
    report: Report,
    action: str,
    payload: str,
    expected: str,
    key: str,
    message_id: int,
) -> None:
    """Quiet mode uses the EHS silence message rather than the AC quiet message."""
    target = entity_id(hass, "switch", key)
    assert hass.states.get(target).state == "unknown"
    report("200000", message_id, payload)
    await hass.async_block_till_done()
    assert hass.states.get(target).state == expected
    await hass.services.async_call(
        "switch", action, {"entity_id": target}, blocking=True
    )
    call = mock_nasa.return_value.devices["200000"].write_attribute.await_args
    assert message_id == call.args[0].MESSAGE_ID
    assert call.kwargs["value"] == bool(int(payload, 16))


async def test_null_value(hass: HomeAssistant, report: Report) -> None:
    """A missing reported switch value remains unknown."""
    report("200000", 0x4046, None)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "switch", "quiet_mode")).state == "unknown"
