"""Test entry setup and teardown through Home Assistant."""

from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsungehs import async_unload_entry

from . import entity_id


async def test_setup(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Every platform creates entities and the connection starts once."""
    assert integration.state is ConfigEntryState.LOADED
    mock_nasa.return_value.start.assert_awaited_once()
    assert {state.domain for state in hass.states.async_all()} == {
        "climate",
        "sensor",
        "binary_sensor",
        "water_heater",
        "switch",
        "number",
        "select",
    }
    assert hass.states.get(entity_id(hass, "climate", "heating")).state == "off"


async def test_unload(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Unloading removes states, callbacks and polling."""
    assert await hass.config_entries.async_unload(integration.entry_id)
    await hass.async_block_till_done()
    assert integration.state is ConfigEntryState.NOT_LOADED
    assert all(state.state == "unavailable" for state in hass.states.async_all())
    mock_nasa.return_value.stop.assert_awaited_once()
    for device in mock_nasa.return_value.devices.values():
        assert not device._device_callbacks


async def test_retry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Failed startup is stopped and can be retried without duplicate entities."""
    mock_config_entry.add_to_hass(hass)
    mock_nasa.return_value.start.side_effect = ConnectionError
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    mock_nasa.return_value.stop.assert_awaited_once()
    mock_nasa.return_value.start.side_effect = None
    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_metadata_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """A failure while reading device identity follows the setup retry path."""
    mock_nasa.return_value.devices["200000"].get_attribute.side_effect = TimeoutError
    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    mock_nasa.return_value.stop.assert_awaited_once()


async def test_migration(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """Legacy host and numeric-string port migrate through HA setup."""
    entry = MockConfigEntry(
        domain="samsungehs",
        data={"host": "192.0.2.1", "port": "8888"},
        options={"retained": True},
        version=1,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.version == 2
    assert entry.data == {"device": "socket://192.0.2.1:8888"}
    assert entry.unique_id == "socket://192.0.2.1:8888"
    assert entry.options == {"retained": True}


async def test_future_version(hass: HomeAssistant, mock_nasa: MagicMock) -> None:
    """Unknown future entry versions cannot load."""
    entry = MockConfigEntry(domain="samsungehs", data={"device": "unused"}, version=3)
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
    mock_nasa.return_value.start.assert_not_awaited()


async def test_reload(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """Reload retains entity IDs without accumulating device callbacks."""
    before = {state.entity_id for state in hass.states.async_all()}
    counts = {
        address: len(device._device_callbacks)
        for address, device in mock_nasa.return_value.devices.items()
    }
    assert await hass.config_entries.async_reload(integration.entry_id)
    await hass.async_block_till_done()
    assert {state.entity_id for state in hass.states.async_all()} == before
    assert {
        address: len(device._device_callbacks)
        for address, device in mock_nasa.return_value.devices.items()
    } == counts


async def test_options_reload(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """An options update reloads the active entry once."""
    hass.config_entries.async_update_entry(integration, options={"changed": True})
    await hass.async_block_till_done()
    assert integration.state is ConfigEntryState.LOADED
    assert mock_nasa.return_value.start.await_count == 2
    mock_nasa.return_value.stop.assert_awaited_once()


async def test_failed_unload(
    hass: HomeAssistant, integration: MockConfigEntry, mock_nasa: MagicMock
) -> None:
    """A failed platform unload keeps the entry and live connection usable."""
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ):
        assert not await hass.config_entries.async_unload(integration.entry_id)
    try:
        assert integration.state is ConfigEntryState.FAILED_UNLOAD
        mock_nasa.return_value.stop.assert_not_awaited()
    finally:
        # HA makes failed unloads non-recoverable. Release the test resources.
        assert await async_unload_entry(hass, integration)
