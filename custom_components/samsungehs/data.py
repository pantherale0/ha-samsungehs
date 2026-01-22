"""Custom types for samsungehs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from pysamsungnasa import SamsungNasa

    from .coordinator import SamsungEhsDataUpdateCoordinator


@dataclass
class SamsungEhsData:
    """Data for the Samsung EHS integration."""

    client: SamsungNasa
    coordinator: SamsungEhsDataUpdateCoordinator
    messages_to_read: dict[str, list[int]] = field(default_factory=dict)
    first_run_messages: dict[str, list[int]] = field(default_factory=dict)


type SamsungEhsConfigEntry = ConfigEntry[SamsungEhsData]
