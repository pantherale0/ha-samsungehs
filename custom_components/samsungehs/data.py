"""Custom types for samsungehs."""

from __future__ import annotations

from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from pysamsungnasa import SamsungNasa
from .coordinator import SamsungEhsDataUpdateCoordinator


type SamsungEhsConfigEntry = ConfigEntry[SamsungEhsData]


@dataclass
class SamsungEhsData:
    """Data for the Samsung EHS integration."""

    client: SamsungNasa
    coordinator: SamsungEhsDataUpdateCoordinator
