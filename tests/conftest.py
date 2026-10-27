"""Home Assistant fixtures with the NASA library mocked at the I/O boundary."""

from collections.abc import Callable, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pysamsungnasa import SamsungNasa
from pysamsungnasa.protocol.factory.messages import MESSAGE_PARSERS
from pysamsungnasa.protocol.factory.messages.basic import (
    DbCodeMiComMainMessage,
    ProductModelName,
    SerialNumber,
)
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    load_json_object_fixture,
)
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from custom_components.samsungehs.const import DOMAIN

from . import DEVICE_URL, Report


@pytest.fixture(autouse=True)
def custom_integrations(request: pytest.FixtureRequest) -> None:
    """Enable custom integrations without initializing HA for standalone tests."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Store HA snapshots beside the consuming tests."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a connection with one indoor and one outdoor device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Samsung EHS",
        unique_id=DEVICE_URL,
        data={"device": DEVICE_URL},
        version=2,
        entry_id="connection",
        subentries_data=[
            {
                "subentry_id": address,
                "subentry_type": "device",
                "unique_id": address,
                "title": address,
                "data": {},
            }
            for address in ("200000", "100000")
        ],
    )


@pytest.fixture
def nasa_client_factory() -> Callable[[str, list[str]], SamsungNasa]:
    """Create independent real NASA devices with mocked transport operations."""

    def create(device_url: str, addresses: list[str]) -> SamsungNasa:
        client = SamsungNasa(
            config={"device_path": device_url, "device_addresses": addresses}
        )
        client.start = AsyncMock()
        client.stop = AsyncMock()
        client.send_message = AsyncMock()
        client.client.nasa_read = AsyncMock()
        client.client._is_connected = True
        client.client.writer = MagicMock()
        client.client.writer.is_closing.return_value = False
        for device in client.devices.values():
            device.attributes.update(
                {
                    ProductModelName.MESSAGE_ID: ProductModelName(
                        value={"model_name": "AE080", "model_type": "EHS"}
                    ),
                    SerialNumber.MESSAGE_ID: SerialNumber(value="TEST-SERIAL"),
                    DbCodeMiComMainMessage.MESSAGE_ID: DbCodeMiComMainMessage(
                        value="1.0"
                    ),
                }
            )
            device.get_attribute = AsyncMock(
                side_effect=lambda attribute, **_: attribute(value=None)
            )
            device.write_attribute = AsyncMock()
            device.write_attributes = AsyncMock()
        return client

    return create


@pytest.fixture
def mock_nasa(
    nasa_client_factory: Callable[[str, list[str]], SamsungNasa],
) -> Generator[MagicMock]:
    """Patch the integration's client constructor and retain real device callbacks."""
    with patch(
        "custom_components.samsungehs.SamsungNasa", autospec=True
    ) as constructor:
        constructor.return_value = nasa_client_factory(DEVICE_URL, ["200000", "100000"])
        yield constructor


@pytest.fixture
async def integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_nasa: MagicMock
) -> MockConfigEntry:
    """Load every platform through the config-entry manager."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry


@pytest.fixture
def report(hass: HomeAssistant, mock_nasa: MagicMock) -> Report:
    """Deliver a device report through the callbacks installed by real entities."""

    def deliver(address: str, message_id: int, payload: str | None) -> None:
        device = mock_nasa.return_value.devices[address]
        message = (
            MESSAGE_PARSERS[message_id](value=None)
            if payload is None
            else MESSAGE_PARSERS[message_id].parse_payload(bytes.fromhex(payload))
        )
        device.handle_packet(
            messageNumber=message_id,
            packet=message,
            dest="510000",
            formattedMessageNumber=hex(message_id),
        )

    return deliver


@pytest.fixture
async def indoor_reports(
    hass: HomeAssistant, integration: MockConfigEntry, report: Report
) -> None:
    """Publish a fixed device report used by platform behavior tests."""
    for message_id, payload in load_json_object_fixture("indoor.json").items():
        report("200000", int(message_id, 16), payload)
    await hass.async_block_till_done()
