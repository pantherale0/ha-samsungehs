"""Adds config flow for Samsung EHS."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN

MAIN_STEP_USER = vol.Schema(
    {
        vol.Required(
            CONF_DEVICE,
        ): selector.SerialPortSelector()
    },
)

SUB_STEP_USER = vol.Schema(
    {
        vol.Required("address"): selector.TextSelector(),
    }
)


class SamsungEhsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Samsung EHS."""

    VERSION = 2

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: config_entries.ConfigEntry
    ) -> dict[str, type[config_entries.ConfigSubentryFlow]]:
        return {"device": SamsungEhsDeviceSubentry}

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            await self.async_set_unique_id(unique_id=user_input[CONF_DEVICE])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_DEVICE],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                MAIN_STEP_USER,
                user_input or {},
            ),
            errors=_errors,
        )


class SamsungEhsDeviceSubentry(config_entries.ConfigSubentryFlow):
    """Sub entry config flow for devices on the Samsung EHS protocol."""

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.SubentryFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=user_input["address"],
                data={},
                unique_id=user_input["address"],
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                SUB_STEP_USER,
                user_input or {},
            ),
            errors=_errors,
        )
