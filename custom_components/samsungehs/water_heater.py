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
from pysamsungnasa.helpers import Address
from pysamsungnasa.protocol.enum import AddressClass, DataType, DhwOpMode
from pysamsungnasa.protocol.factory.messages.indoor import (
    DhwCurrentTemperature,
    DhwTargetTemperature,
    InDhwOpMode,
    InDhwWaterHeaterPower,
)

from .entity import SamsungEhsEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
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
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(
            coordinator,
            message=None,
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
        value = self.get_attribute(DhwCurrentTemperature)
        return float(value) if value is not None else None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        value = self.get_attribute(DhwTargetTemperature)
        return float(value) if value is not None else None

    @property
    def current_operation(self) -> str | None:
        """Return the current operation."""
        # Check if DHW is off first
        if not self.get_attribute(InDhwWaterHeaterPower):
            return STATE_OFF
        op_mode = self.get_attribute(InDhwOpMode)
        if op_mode is None or not isinstance(op_mode, DhwOpMode):
            return None
        return EHS_TO_HASS_STATE.get(op_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        await self._device.write_attribute(
            DhwTargetTemperature, kwargs["temperature"], mode=DataType.REQUEST
        )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        if operation_mode == STATE_OFF:
            await self.async_turn_off()
            return
        # Turn dhw power on and send new mode.
        await self._device.write_attributes(
            {
                InDhwWaterHeaterPower: True,
                InDhwOpMode: HASS_TO_EHS_STATE[operation_mode],
            },
            mode=DataType.REQUEST,
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the water heater on."""
        await self._device.write_attribute(InDhwWaterHeaterPower, value=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the water heater off."""
        await self._device.write_attribute(InDhwWaterHeaterPower, value=False)

    async def async_added_to_hass(self) -> None:
        """Call when the entity is added to HASS."""
        # Read some attributes by hand on startup to ensure we have the correct state.
        await super().async_added_to_hass()  # Ensure essentials is registered first
        try:
            await self._device.get_attribute(DhwTargetTemperature, requires_read=True)
            await self._device.get_attribute(DhwCurrentTemperature, requires_read=True)
            await self._device.get_attribute(InDhwOpMode, requires_read=True)
            await self._device.get_attribute(InDhwWaterHeaterPower, requires_read=True)
        except TimeoutError:
            pass  # If it does not respond, we will get it on the next update cycle.
