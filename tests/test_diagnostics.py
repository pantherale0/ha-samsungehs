"""Tests for Samsung EHS diagnostics."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace

from custom_components.samsungehs.diagnostics import (
    async_get_config_entry_diagnostics,
)


def test_diagnostics_redact_connection_and_device_identifiers() -> None:
    """Diagnostics include attributes without exposing device addresses."""
    message = SimpleNamespace(
        as_dict={
            "message_id": 0x1234,
            "message_name": "Example",
            "unit_of_measurement": "C",
            "value": 21.4,
            "is_fsv_message": False,
        }
    )
    device = SimpleNamespace(address="ABC123", attributes={0x1234: message})
    entry = SimpleNamespace(
        data={"device": "******192.0.2.1:1234"},
        options={"host": "192.0.2.1", "port": 1234},
        version=2,
        minor_version=1,
        subentries={
            "device": SimpleNamespace(
                subentry_type="device",
                data={},
                unique_id="ABC123",
                title="ABC123",
            )
        },
        runtime_data=SimpleNamespace(
            client=SimpleNamespace(
                client=SimpleNamespace(is_connected=True),
                devices={"ABC123": device},
            ),
            coordinator=SimpleNamespace(
                last_update_success=True,
                update_interval=timedelta(seconds=15),
            ),
        ),
    )

    diagnostics = asyncio.run(async_get_config_entry_diagnostics(None, entry))

    assert diagnostics == {
        "config_entry": {
            "version": 2,
            "minor_version": 1,
            "data": {"device": "**REDACTED**"},
            "options": {"host": "**REDACTED**", "port": "**REDACTED**"},
            "subentries": [
                {
                    "type": "device",
                    "data": {},
                    "attributes": {
                        "0x1234": {
                            "message_id": 0x1234,
                            "message_name": "Example",
                            "unit_of_measurement": "C",
                            "value": 21.4,
                            "is_fsv_message": False,
                        }
                    },
                }
            ],
        },
        "runtime_data": {
            "client": {"connected": True, "device_count": 1},
            "coordinator": {
                "last_update_success": True,
                "update_interval_seconds": 15.0,
            },
        },
    }


def test_diagnostics_handles_missing_device() -> None:
    """Diagnostics still load when a configured device is not connected."""
    entry = SimpleNamespace(
        data={},
        options={},
        version=2,
        minor_version=1,
        subentries={
            "device": SimpleNamespace(
                subentry_type="device",
                data={},
                unique_id="ABC123",
            )
        },
        runtime_data=SimpleNamespace(
            client=SimpleNamespace(
                client=SimpleNamespace(is_connected=False),
                devices={},
            ),
            coordinator=SimpleNamespace(
                last_update_success=False,
                update_interval=timedelta(seconds=15),
            ),
        ),
    )

    diagnostics = asyncio.run(async_get_config_entry_diagnostics(None, entry))

    assert diagnostics["config_entry"]["subentries"][0]["attributes"] == {}
