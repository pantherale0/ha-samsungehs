"""Coordinator batching, reconnects and scheduled state recovery."""

from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pysamsungnasa.protocol.enum import DataType
from pysamsungnasa.protocol.factory.messages.indoor import InTargetTemperature
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from . import Report, entity_id

pytestmark = pytest.mark.platforms("sensor")


@pytest.mark.parametrize(
    ("count", "batches"),
    [
        (0, []),
        (1, [[0]]),
        (10, [list(range(10))]),
        (11, [list(range(10)), [10]]),
        (21, [list(range(10)), list(range(10, 20)), [20]]),
    ],
)
async def test_batches(
    integration: MockConfigEntry,
    mock_nasa: MagicMock,
    count: int,
    batches: list[list[int]],
) -> None:
    """Initial reads occur once and recurring reads respect ten-message limits."""
    runtime = integration.runtime_data
    runtime.first_run_messages = {"200000": list(range(count))}
    runtime.messages_to_read = {"100000": list(range(count))}
    runtime.coordinator._first_refresh = True
    read = mock_nasa.return_value.client.nasa_read
    read.reset_mock()
    await runtime.coordinator.async_refresh()
    assert read.await_args_list == [
        call(batch, address) for address in ("200000", "100000") for batch in batches
    ]
    read.reset_mock()
    await runtime.coordinator.async_refresh()
    assert read.await_args_list == [call(batch, "100000") for batch in batches]


async def test_scheduled_recovery(
    hass: HomeAssistant,
    integration: MockConfigEntry,
    mock_nasa: MagicMock,
    freezer: FrozenDateTimeFactory,
    report: Report,
) -> None:
    """The actual periodic refresh publishes unavailable and recovered states."""
    report("200000", 0x4237, "0176")
    await hass.async_block_till_done()
    target = entity_id(hass, "sensor", "dhw_tank_temperature")
    assert hass.states.get(target).state == "37.4"
    client = mock_nasa.return_value
    client.client.nasa_read.side_effect = TimeoutError
    freezer.tick(timedelta(seconds=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(target).state == "unavailable"
    client.client.nasa_read.side_effect = None
    client.client._is_connected = False
    client.start.reset_mock()
    client.start.side_effect = lambda: setattr(client.client, "_is_connected", True)
    freezer.tick(timedelta(seconds=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    client.start.assert_awaited_once()
    assert hass.states.get(target).state == "37.4"


async def test_first_read_retry(
    integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Failed initial reads are retried on the next refresh."""
    runtime = integration.runtime_data
    runtime.first_run_messages = {"200000": [0x4237]}
    runtime.messages_to_read = {}
    runtime.coordinator._first_refresh = True
    read = mock_nasa.return_value.client.nasa_read
    read.reset_mock()
    read.side_effect = TimeoutError
    await runtime.coordinator.async_refresh()
    assert not runtime.coordinator.last_update_success
    read.side_effect = None
    await runtime.coordinator.async_refresh()
    assert read.await_args_list == [call([0x4237], "200000"), call([0x4237], "200000")]


async def test_write_message(
    integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Coordinator commands preserve the selected address and message."""
    message = InTargetTemperature(value=21.0)
    await integration.runtime_data.coordinator.write_message(
        "200000", DataType.REQUEST, message
    )
    mock_nasa.return_value.send_message.assert_awaited_once_with(
        "200000", request_type=DataType.REQUEST, messages=[message]
    )
