"""Diagnostics are exercised through HA's authenticated HTTP endpoint."""

import json
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion


@pytest.mark.parametrize("connected", [True, False])
async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    integration: MockConfigEntry,
    mock_nasa: MagicMock,
    snapshot: SnapshotAssertion,
    *,
    connected: bool,
) -> None:
    """Identity values are redacted while useful runtime data remains."""
    mock_nasa.return_value.client._is_connected = connected
    original_data = dict(integration.data)
    data = await get_diagnostics_for_config_entry(hass, hass_client, integration)
    serialized = json.dumps(data)
    for private in ("192.0.2.1", "8888", "200000", "100000", "TEST-SERIAL"):
        assert private not in serialized
    assert data == snapshot
    assert dict(integration.data) == original_data


async def test_missing_device(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    integration: MockConfigEntry,
    mock_nasa: MagicMock,
    snapshot: SnapshotAssertion,
) -> None:
    """A configured device may disappear before diagnostics are requested."""
    device = mock_nasa.return_value.devices.pop("200000")
    integration.runtime_data.coordinator.update_interval = None
    data = await get_diagnostics_for_config_entry(hass, hass_client, integration)
    assert data["config_entry"]["subentries"][0]["attributes"] == {}
    assert data["runtime_data"]["coordinator"]["update_interval_seconds"] is None
    assert data == snapshot
    mock_nasa.return_value.devices["200000"] = device
