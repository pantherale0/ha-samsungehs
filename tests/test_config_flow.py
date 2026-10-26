"""Check the device address entered when adding a NASA device."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.samsungehs.config_flow import (
    SamsungEhsDeviceSubentry,
    normalize_address,
)

COMPONENT = Path(__file__).parents[1] / "custom_components" / "samsungehs"


@pytest.mark.parametrize(
    ("entered", "address"),
    [
        ("200000", "200000"),
        ("20.00.00", "200000"),
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
def test_normalize_address(entered: str, address: str | None) -> None:
    """Dotted and lower-case forms become the six-digit form the library uses."""
    assert normalize_address(entered) == address


def run_step(entered: str) -> MagicMock:
    """Submit the address form and return the flow's mocked result methods."""
    flow = SamsungEhsDeviceSubentry()
    flow.async_create_entry = MagicMock()
    flow.async_show_form = MagicMock()
    flow.add_suggested_values_to_schema = MagicMock()
    asyncio.run(flow.async_step_user({"address": entered}))
    return flow


def test_dotted_address_creates_device() -> None:
    """20.00.00 is stored as 200000, the key pysamsungnasa uses for the device."""
    flow = run_step("20.00.00")
    flow.async_create_entry.assert_called_once_with(
        title="200000", data={}, unique_id="200000"
    )
    flow.async_show_form.assert_not_called()


def test_invalid_address_shows_error() -> None:
    """An address that isn't six hex digits shows a form error instead of failing."""
    flow = run_step("20.00")
    flow.async_create_entry.assert_not_called()
    assert flow.async_show_form.call_args.kwargs["errors"] == {
        "address": "invalid_address"
    }


@pytest.mark.parametrize("file_name", ["strings.json", "translations/en.json"])
def test_invalid_address_message(file_name: str) -> None:
    """The form error has a message."""
    strings = json.loads((COMPONENT / file_name).read_text(encoding="utf-8"))

    assert strings["config_subentries"]["device"]["error"]["invalid_address"]
