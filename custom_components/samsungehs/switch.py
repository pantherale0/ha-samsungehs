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
    DataType,
    SamsungEnum,
)
from pysamsungnasa.protocol.factory import SendMessage

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry


class SamsungEHSSwitchKey(StrEnum):
    """Samsung EHS Switch Keys."""

    OUTING_MODE = "outing_mode"
    QUIET_MODE = "quiet_mode"


@dataclass(frozen=True, kw_only=True)
class SamsungEHSSwitchEntityDescription(SwitchEntityDescription):
    """Describes Samsung EHS switch entity."""

    on_state: SamsungEnum | bool
    off_state: SamsungEnum | bool
    message_number: int
    requires_read: bool = False


SWITCHES: tuple[SamsungEHSSwitchEntityDescription, ...] = (
    SamsungEHSSwitchEntityDescription(
        key=SamsungEHSSwitchKey.OUTING_MODE,
        translation_key=SamsungEHSSwitchKey.OUTING_MODE,
        message_number=0x406D,
        on_state=True,
        off_state=False,
    ),
    SamsungEHSSwitchEntityDescription(
        key=SamsungEHSSwitchKey.QUIET_MODE,
        translation_key=SamsungEHSSwitchKey.QUIET_MODE,
        message_number=0x406E,
        on_state=True,
        off_state=False,
        requires_read=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Samsung EHS switch based on a config entry."""
    for subentry in entry.subentries.values():
        if not subentry.unique_id:
            continue
        if Address.parse(subentry.unique_id).class_id != AddressClass.INDOOR:
            continue
        async_add_entities(
            SamsungEHSSwitch(entry.runtime_data.coordinator, description, subentry)
            for description in SWITCHES
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
            message_number=description.message_number,
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
        if self.entity_description.message_number not in self._device.attributes:
            return None
        return (
            self._device.attributes[self.entity_description.message_number]
            == self.entity_description.on_state
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        new_value = self.entity_description.on_state
        if isinstance(new_value, bool):
            new_value = new_value.to_bytes(1, "big")
        elif isinstance(new_value, SamsungEnum):
            new_value = int(new_value.value).to_bytes(1, "big")
        else:
            return
        await self.coordinator.write_message(
            self._device_address,
            request_type=DataType.WRITE,
            message=SendMessage(
                MESSAGE_ID=self.entity_description.message_number,
                PAYLOAD=new_value,
            ),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        new_value = self.entity_description.off_state
        if isinstance(new_value, bool):
            new_value = new_value.to_bytes(1, "big")
        elif isinstance(new_value, SamsungEnum):
            new_value = int(new_value.value).to_bytes(1, "big")
        else:
            return
        await self.coordinator.write_message(
            self._device_address,
            request_type=DataType.WRITE,
            message=SendMessage(
                MESSAGE_ID=self.entity_description.message_number,
                PAYLOAD=new_value,
            ),
        )
