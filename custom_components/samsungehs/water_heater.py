"""Water Heater for Samsung EHS (DHW)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_HEAT_PUMP,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import STATE_OFF, UnitOfTemperature
from pysamsungnasa.device import IndoorNasaDevice
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import AddressClass, DhwOpMode

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SamsungEhsDataUpdateCoordinator
    from .data import SamsungEhsConfigEntry

EHS_TO_HASS_STATE = {
    DhwOpMode.ECO: STATE_ECO,
    DhwOpMode.STANDARD: STATE_HEAT_PUMP,
    DhwOpMode.POWER: STATE_PERFORMANCE,
    DhwOpMode.FORCE: STATE_ELECTRIC,
}

HASS_TO_EHS_STATE = {
    STATE_ECO: DhwOpMode.ECO,
    STATE_HEAT_PUMP: DhwOpMode.STANDARD,
    STATE_PERFORMANCE: DhwOpMode.POWER,
    STATE_ELECTRIC: DhwOpMode.FORCE,
}

SUPPORTED_STATES = [
    STATE_OFF,
    STATE_ECO,
    STATE_HEAT_PUMP,
    STATE_PERFORMANCE,
    STATE_ELECTRIC,
]

ENTITY_DESCRIPTIONS: tuple[WaterHeaterEntityDescription, ...] = (
    WaterHeaterEntityDescription(key="dhw"),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument
    entry: SamsungEhsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the water heater platform."""
    for subentry in entry.subentries.values():
        assert subentry.unique_id is not None  # noqa: S101
        address = Address.parse(subentry.unique_id)
        if address.class_id != AddressClass.INDOOR:
            continue
        async_add_entities(
            [
                SamsungEhsWaterHeater(
                    coordinator=entry.runtime_data.coordinator,
                    entity_description=entity_description,
                    subentry=subentry,
                )
                for entity_description in ENTITY_DESCRIPTIONS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class SamsungEhsWaterHeater(SamsungEhsEntity, WaterHeaterEntity):
    """Samsung EHS Water Heater class."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = SUPPORTED_STATES
    _attr_translation_key = "dhw"

    def __init__(
        self,
        coordinator: SamsungEhsDataUpdateCoordinator,
        entity_description: WaterHeaterEntityDescription,
        subentry,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(
            coordinator,
            message_number=None,
            key=entity_description.key,
            subentry=subentry,
        )
        self.entity_description = entity_description

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.ON_OFF
            | WaterHeaterEntityFeature.OPERATION_MODE
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self._device is None:
            return None
        if (
            isinstance(self._device, IndoorNasaDevice)
            and self._device.dhw_controller is not None
        ):
            return self._device.dhw_controller.current_temperature
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self._device is None:
            return None
        if (
            isinstance(self._device, IndoorNasaDevice)
            and self._device.dhw_controller is not None
        ):
            return self._device.dhw_controller.target_temperature
        return None

    @property
    def current_operation(self) -> str | None:
        """Return the current operation."""
        # Check if DHW is off first
        if (
            self._device is None
            or not isinstance(self._device, IndoorNasaDevice)
            or self._device.dhw_controller is None
        ):
            return None
        if (
            self._device.dhw_controller.power is None
            or not self._device.dhw_controller.power
            or self._device.dhw_controller.operation_mode is None
        ):
            return STATE_OFF
        return EHS_TO_HASS_STATE.get(self._device.dhw_controller.operation_mode)

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return not (
            self._device is None
            or not isinstance(self._device, IndoorNasaDevice)
            or self._device.dhw_controller is None
        )

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if not self.available:
            return
        assert isinstance(self._device, IndoorNasaDevice)
        assert self._device.dhw_controller is not None
        await self._device.dhw_controller.set_target_temperature(kwargs["temperature"])

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        if not self.available:
            return
        assert isinstance(self._device, IndoorNasaDevice)
        assert self._device.dhw_controller is not None
        if operation_mode == STATE_OFF:
            await self._device.dhw_controller.turn_off()
            return
        # Turn dhw power on and send new mode.
        if (
            self._device.dhw_controller.power is None
            or not self._device.dhw_controller.power
        ):
            await self._device.dhw_controller.turn_on()
        await self._device.dhw_controller.set_operation_mode(
            HASS_TO_EHS_STATE[operation_mode]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the water heater on."""
        if not self.available:
            return
        assert isinstance(self._device, IndoorNasaDevice)
        assert self._device.dhw_controller is not None
        await self._device.dhw_controller.turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the water heater off."""
        if not self.available:
            return
        assert isinstance(self._device, IndoorNasaDevice)
        assert self._device.dhw_controller is not None
        await self._device.dhw_controller.turn_off()
