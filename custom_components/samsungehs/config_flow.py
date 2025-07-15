"""Adds config flow for Samsung EHS."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector
from pysamsungnasa.protocol.factory import MESSAGE_PARSERS

from .const import DOMAIN


def msg_parser_list() -> list[selector.SelectOptionDict]:
    """Return MESSAGE_PARSERS in a organised list for Home Assistant."""
    data = [
        selector.SelectOptionDict(
            value=str(k),
            label=f"{v.MESSAGE_NAME}",
        )
        for k, v in MESSAGE_PARSERS.items()
    ]
    data.sort(key=lambda x: x["label"])
    return data


MAIN_STEP_USER = vol.Schema(
    {
        vol.Required(
            CONF_HOST,
        ): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT,
            ),
        ),
        vol.Required(CONF_PORT): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=65535,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="",
            ),
        ),
    },
)

SUB_STEP_USER = vol.Schema(
    {
        vol.Required("address"): selector.TextSelector(),
        vol.Optional("sensors"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=True,
                options=msg_parser_list(),
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


class SamsungEhsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

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
            await self.async_set_unique_id(unique_id=user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_HOST],
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
    """Sub entry config flow for devices on the NASA protocol."""

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.SubentryFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=user_input["address"],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                SUB_STEP_USER,
                user_input or {},
            ),
            errors=_errors,
        )
