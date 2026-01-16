"""Samsung EHS Climate platform."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import (
    AddressClass,
    InOperationMode,
    InOperationPower,
    OutdoorIndoorDefrostStep,
    OutdoorOperationStatus,
)
from pysamsungnasa.protocol.factory.messages.indoor import (
    InWaterLawTargetTemperature,
    IndoorFlowTemperature,
    InOperationModeMessage,
    InOperationPowerMessage,
    InRoomTemperature,
    InTargetTemperature,
    InWaterOutletTargetTemperature,
)
from pysamsungnasa.protocol.factory.messages.outdoor import (
    OutdoorDefrostStatus,
    OutdoorOperationStatusMessage,
)

from .entity import SamsungEhsEntity
from .helpers import (
    async_set_space_heating_target_temperature,
    get_temperature_control_mode,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from custom_components.samsungehs.coordinator import SamsungEhsDataUpdateCoordinator

    from .data import SamsungEhsConfigEntry

EHS_OP_TO_HASS = {
    InOperationMode.AUTO: HVACMode.AUTO,
    InOperationMode.COOL: HVACMode.COOL,
    InOperationMode.HEAT: HVACMode.HEAT,
    InOperationMode.FAN: HVACMode.FAN_ONLY,
    None: HVACMode.OFF,
}

HASS_TO_EHS_OP = {v: k for k, v in EHS_OP_TO_HASS.items()}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the water heater platform."""
    for subentry in entry.subentries.values():
        assert subentry.unique_id is not None  # noqa: S101
        address = Address.parse(subentry.unique_id)
        if address.class_id == AddressClass.INDOOR:
            async_add_entities(
                [
                    SamsungEhsClimate(
                        coordinator=entry.runtime_data.coordinator,
                        subentry=subentry,
                    )
                ],
                config_subentry_id=subentry.subentry_id,
            )


class SamsungEhsClimate(SamsungEhsEntity, ClimateEntity):
    """Samsung EHS Climate."""

    _attr_hvac_modes: ClassVar[list[HVACMode]] = list(EHS_OP_TO_HASS.values())
    _attr_supported_features = (
        ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TARGET_TEMPERATURE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_translation_key = "heating"
    _attr_target_temperature_step = 0.1

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            subentry=subentry,
            message=None,
            key="heating",
        )  # No message number for this mode.

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        if not self.available:
            return None
        control_mode = get_temperature_control_mode(self._device)
        if control_mode == "target_room_temperature":
            value = self.get_attribute(InRoomTemperature)
        elif control_mode == "target_water_temperature":
            value = self.get_attribute(IndoorFlowTemperature)
        elif control_mode == "water_law_offset":
            value = self.get_attribute(InWaterLawTargetTemperature)
        else:
            return None
        return (
            float(value) if value is not None and not isinstance(value, str) else None
        )

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        if not self.available:
            return None
        control_mode = get_temperature_control_mode(self._device)
        if control_mode == "target_room_temperature":
            value = self.get_attribute(InTargetTemperature)
        elif control_mode == "target_water_temperature":
            value = self.get_attribute(InWaterOutletTargetTemperature)
        elif control_mode == "water_law_offset":
            value = self.get_attribute(InWaterLawTargetTemperature)
        else:
            return None
        return (
            float(value) if value is not None and not isinstance(value, str) else None
        )

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current operation."""
        if not self.available:
            return None
        if self.get_attribute(InOperationPowerMessage) == InOperationPower.OFF:
            return HVACMode.OFF
        return EHS_OP_TO_HASS.get(self.get_attribute(InOperationModeMessage))

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current operation."""
        if (
            self.hvac_mode == HVACMode.COOL
            and self.get_attribute(InOperationPowerMessage) != InOperationPower.OFF
            and self.get_attribute(OutdoorOperationStatusMessage)
            == OutdoorOperationStatus.OP_NORMAL
        ):
            return HVACAction.COOLING
        if (
            self.hvac_mode == HVACMode.HEAT
            and self.get_attribute(InOperationPowerMessage) != InOperationPower.OFF
            and self.get_attribute(OutdoorOperationStatusMessage)
            == OutdoorOperationStatus.OP_NORMAL
        ):
            return HVACAction.HEATING
        if (
            self.get_attribute(OutdoorOperationStatusMessage)
            == OutdoorOperationStatus.OP_SAFETY
        ):
            return HVACAction.PREHEATING
        if (
            self.get_attribute(OutdoorDefrostStatus)
            != OutdoorIndoorDefrostStep.NO_DEFROST_OPERATION
        ):
            return HVACAction.DEFROSTING
        if self.get_attribute(InOperationPowerMessage) == InOperationPower.OFF:
            return HVACAction.OFF
        return HVACAction.IDLE

    @property
    def min_temp(self) -> float | None:
        """Return the minimum temperature."""
        return -5.0

    @property
    def max_temp(self) -> float | None:
        """Return the maximum temperature."""
        return 50.0

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        await async_set_space_heating_target_temperature(
            self._device, kwargs["temperature"]
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target operation mode."""
        if self.available:
            if hvac_mode == HVACMode.OFF:
                await self.async_turn_off()
                return
            await self._device.write_attribute(
                InOperationModeMessage, HASS_TO_EHS_OP[hvac_mode]
            )
            await self.async_turn_on()

    async def async_turn_off(self) -> None:
        """Turn the climate off."""
        await self._device.write_attribute(
            InOperationPowerMessage, InOperationPower.OFF
        )

    async def async_turn_on(self) -> None:
        """Turn the climate on."""
        await self._device.write_attribute(
            InOperationPowerMessage, InOperationPower.ON_STATE_1
        )

    async def async_added_to_hass(self) -> None:
        """Call when the entity is added to HASS."""
        # We need to add a subscription for the outdoor operation status to determine hvac_action  # noqa: E501
        self.coordinator.config_entry.runtime_data.client.parser.add_packet_listener(
            OutdoorOperationStatusMessage.MESSAGE_ID, self._device.handle_packet
        )
        self.coordinator.config_entry.runtime_data.client.parser.add_packet_listener(
            OutdoorDefrostStatus.MESSAGE_ID, self._device.handle_packet
        )
        return await super().async_added_to_hass()
