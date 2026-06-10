"""Config and options flow for the Minecraft Broker."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    BrokerAuthError,
    BrokerClient,
    BrokerConnectionError,
    BrokerError,
)
from .const import (
    ACTION_STATUS,
    CONF_BEARER_TOKEN,
    CONF_HMAC_KEY,
    CONF_INSTANCES,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _parse_instances(raw: str) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


async def _validate(hass, url: str, bearer: str, hmac_key: str) -> None:
    """Probe the broker with a ``status`` call to validate connection + auth."""
    session = async_get_clientsession(hass)
    client = BrokerClient(session, url, bearer, hmac_key, timeout=30.0)
    await client.async_call(ACTION_STATUS)


class MinecraftBrokerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip()
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            try:
                await _validate(
                    self.hass,
                    url,
                    user_input[CONF_BEARER_TOKEN],
                    user_input[CONF_HMAC_KEY],
                )
            except BrokerAuthError:
                errors["base"] = "invalid_auth"
            except BrokerConnectionError:
                errors["base"] = "cannot_connect"
            except BrokerError:
                errors["base"] = "unknown"
            else:
                instances = _parse_instances(user_input.get(CONF_INSTANCES, ""))
                return self.async_create_entry(
                    title="Minecraft Broker",
                    data={
                        CONF_URL: url,
                        CONF_BEARER_TOKEN: user_input[CONF_BEARER_TOKEN],
                        CONF_HMAC_KEY: user_input[CONF_HMAC_KEY],
                    },
                    options={
                        CONF_INSTANCES: instances,
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Required(CONF_BEARER_TOKEN): str,
                vol.Required(CONF_HMAC_KEY): str,
                vol.Optional(CONF_INSTANCES, default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MinecraftBrokerOptionsFlow(config_entry)


class MinecraftBrokerOptionsFlow(OptionsFlow):
    """Edit the instance list and poll interval after setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_INSTANCES: _parse_instances(user_input.get(CONF_INSTANCES, "")),
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                },
            )

        current_instances = ", ".join(
            self._entry.options.get(CONF_INSTANCES, []) or []
        )
        current_interval = self._entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_INSTANCES, default=current_instances): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): vol.All(int, vol.Range(min=15, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
