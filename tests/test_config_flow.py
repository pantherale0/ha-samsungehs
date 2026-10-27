"""Exercise user, reconfigure and subentry flows through HA's managers."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsungehs.config_flow import normalize_address

from . import DEVICE_URL, DOMAIN


@pytest.mark.parametrize(
    ("entered", "expected"),
    [
        ("200000", "200000"),
        (" 20.00.00 ", "200000"),
        ("20:00:00", "200000"),
        ("10-00-00", "100000"),
        ("62ff00", "62FF00"),
        ("20.00", None),
        ("2000000", None),
        ("20.00.0G", None),
        ("", None),
    ],
)
def test_normalize_address(entered: str, expected: str | None) -> None:
    """Normalize separators and reject malformed device addresses."""
    assert normalize_address(entered) == expected


@pytest.mark.parametrize("device", [DEVICE_URL, "/dev/ttyUSB0"])
async def test_user(hass: HomeAssistant, mock_nasa: MagicMock, device: str) -> None:
    """Persist a serial or network connection with its unique ID."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": device}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == device
    assert result["data"] == {"device": device}
    assert result["result"].unique_id == device
    assert result["result"].version == 2


async def test_duplicate(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An existing connection cannot be added twice."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"device": DEVICE_URL}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize("device", [DEVICE_URL, "socket://192.0.2.2:8888"])
async def test_reconfigure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, device: str
) -> None:
    """Reconfiguration updates persisted identity and can retain the same URL."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload", return_value=True
    ) as reload:
        result = await mock_config_entry.start_reconfigure_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"device": device}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == {"device": device}
    assert mock_config_entry.unique_id == device
    reload.assert_awaited_once_with(mock_config_entry.entry_id)


async def test_reconfigure_collision(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A connection cannot take another entry's identity."""
    mock_config_entry.add_to_hass(hass)
    other = MockConfigEntry(
        domain=DOMAIN, unique_id="other", data={"device": "other"}, version=2
    )
    other.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": "other"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.unique_id == DEVICE_URL


@pytest.mark.parametrize("entered", ["30.00.00", "30:00:00", "300000"])
async def test_subentry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, entered: str
) -> None:
    """Subentries store normalized addresses on their parent connection."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, "device"), context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"address": entered}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["unique_id"] == "300000"
    assert result["data"] == {}
    assert result["title"] == "300000"
    assert [sub.unique_id for sub in mock_config_entry.subentries.values()] == [
        "200000",
        "100000",
        "300000",
    ]


async def test_subentry_recovery(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Correct an invalid address on the same flow and finish successfully."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, "device"),
        context={"source": "user"},
        data={"address": "20.00"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"address": "invalid_address"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"address": "30.00.00"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["unique_id"] == "300000"


async def test_duplicate_subentry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Adding a configured device cannot duplicate its entities."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, "device"),
        context={"source": "user"},
        data={"address": "20.00.00"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(mock_config_entry.subentries) == 2
