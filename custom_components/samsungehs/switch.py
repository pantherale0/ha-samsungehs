# pylint: disable=E1123
"""Switch platform for Samsung EHS integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import (
    AddressClass,
)
from pysamsungnasa.protocol.factory.messages.indoor import (
    InFsv3041,
    InFsv5051,
    InOutingModeMessage,
    InQuietModeMessage,
)

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from pysamsungnasa.protocol.factory.types import BaseMessage

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEHSSwitchKey(StrEnum):
    """Samsung EHS Switch Keys."""

    OUTING_MODE = "outing_mode"
    QUIET_MODE = "quiet_mode"
    FREQUENCY_RATIO_CONTROL = "frequency_ratio_control"
    DHW_DISINFECTION = "dhw_disinfection"


@dataclass(frozen=True, kw_only=True)
class SamsungEHSSwitchEntityDescription(SwitchEntityDescription):
    """Describes Samsung EHS switch entity."""

    message: type[BaseMessage]
    requires_read: bool = False


SWITCHES: tuple[SamsungEHSSwitchEntityDescription, ...] = (
    SamsungEHSSwitchEntityDescription(
        key=SamsungEHSSwitchKey.OUTING_MODE,
        translation_key=SamsungEHSSwitchKey.OUTING_MODE,
        message=InOutingModeMessage,
    ),
    SamsungEHSSwitchEntityDescription(
        key=SamsungEHSSwitchKey.QUIET_MODE,
        translation_key=SamsungEHSSwitchKey.QUIET_MODE,
        message=InQuietModeMessage,
        requires_read=True,
    ),
    SamsungEHSSwitchEntityDescription(
        key=SamsungEHSSwitchKey.FREQUENCY_RATIO_CONTROL,
        translation_key=SamsungEHSSwitchKey.FREQUENCY_RATIO_CONTROL,
        message=InFsv5051,
        requires_read=True,
    ),
    SamsungEHSSwitchEntityDescription(
        key=SamsungEHSSwitchKey.DHW_DISINFECTION,
        translation_key=SamsungEHSSwitchKey.DHW_DISINFECTION,
        message=InFsv3041,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung EHS switch based on a config entry."""
    for subentry in entry.subentries.values():
        if not subentry.unique_id:
            continue
        if Address.parse(subentry.unique_id).class_id != AddressClass.INDOOR:
            continue
        async_add_entities(
            [
                SamsungEHSSwitch(entry.runtime_data.coordinator, description, subentry)
                for description in SWITCHES
            ],
            config_subentry_id=subentry.subentry_id,
        )


class SamsungEHSSwitch(SamsungEhsEntity, SwitchEntity):
    """Representation of a Samsung EHS switch."""

    entity_description: SamsungEHSSwitchEntityDescription

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        description: SamsungEHSSwitchEntityDescription,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator,
            message=description.message,
            key=description.key,
            requires_read=description.requires_read,
            subentry=subentry,
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self._device is None:
            return None
        if (
            self._message is None
            or self._message.MESSAGE_ID not in self._device.attributes
        ):
            return None
        return self._device.attributes[self._message.MESSAGE_ID].VALUE

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._message is None:
            return
        await self._device.write_attribute(self._message, value=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._message is None:
            return
        await self._device.write_attribute(self._message, value=False)
