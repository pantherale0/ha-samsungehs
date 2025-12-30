"""Samsung EHS Climate platform."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityDescription
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
    OutdoorIndoorDefrostStep,
    OutdoorOperationStatus,
)

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
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

ENTITY_DESCRIPTIONS: tuple[ClimateEntityDescription, ...] = (
    ClimateEntityDescription(key="heating"),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the water heater platform."""
    for subentry in entry.subentries.values():
        assert subentry.unique_id is not None  # noqa: S101
        address = Address.parse(subentry.unique_id)
        if address.class_id is AddressClass.INDOOR:
            async_add_entities(
                (
                    SamsungEhsClimate(
                        coordinator=entry.runtime_data.coordinator,
                        entity_description=entity_description,
                        subentry=subentry,
                    )
                    for entity_description in ENTITY_DESCRIPTIONS
                ),
                config_subentry_id=subentry.subentry_id,
            )


class SamsungEhsClimate(SamsungEhsEntity, ClimateEntity):
    """Samsung EHS Climate."""

    _attr_hvac_modes = list(EHS_OP_TO_HASS.values())
    _attr_supported_features = (
        ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TARGET_TEMPERATURE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        entity_description: ClimateEntityDescription,
        subentry,
    ) -> None:
        super().__init__(
            coordinator,
            subentry=subentry,
            message_number=None,
            key=entity_description.key,
        )  # No message number for this mode.
        self.entity_description = entity_description

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self._device is not None and self._device.climate_controller is not None

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        if self.available:
            return self._device.climate_controller.f_current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        if self.available:
            return self._device.climate_controller.f_target_temperature

    @property
    def current_humidity(self) -> float | None:
        """Return current humidity."""
        if self.available:
            return self._device.climate_controller.current_humidity

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current operation."""
        if self.available:
            if (
                self._device.climate_controller.power is None
                or not self._device.climate_controller.power
            ):
                return HVACMode.OFF
            return EHS_OP_TO_HASS.get(self._device.climate_controller.current_mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current operation."""
        if (
            self._device is None
            or self._device.climate_controller is None
            or self._device.climate_controller.power is None
            or self.hvac_mode is None
        ):
            return None
        if (
            self.hvac_mode == HVACMode.COOL
            and self._device.climate_controller.power
            and self._device.climate_controller.outdoor_operation_status
            == OutdoorOperationStatus.OP_NORMAL
        ):
            return HVACAction.COOLING
        if (
            self.hvac_mode == HVACMode.HEAT
            and self._device.climate_controller.power
            and self._device.climate_controller.outdoor_operation_status
            == OutdoorOperationStatus.OP_NORMAL
        ):
            return HVACAction.HEATING
        if (
            self._device.climate_controller.outdoor_operation_status
            == OutdoorOperationStatus.OP_SAFETY
        ):
            return HVACAction.PREHEATING
        if (
            self._device.climate_controller.outdoor_defrost_status
            != OutdoorIndoorDefrostStep.NO_DEFROST_OPERATION
        ):
            return HVACAction.DEFROSTING
        if not self._device.climate_controller.power:
            return HVACAction.OFF
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if self.available:
            await self._device.climate_controller.set_target_temperature(
                kwargs["temperature"]
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target operation mode."""
        if self.available:
            if hvac_mode == HVACMode.OFF:
                await self.async_turn_off()
                return
            await self._device.climate_controller.set_mode(HASS_TO_EHS_OP[hvac_mode])
            await self.async_turn_on()

    async def async_turn_off(self) -> None:
        """Turn the climate off."""
        if self.available:
            await self._device.climate_controller.turn_off()

    async def async_turn_on(self) -> None:
        """Turn the climate on."""
        if self.available:
            await self._device.climate_controller.turn_on()
