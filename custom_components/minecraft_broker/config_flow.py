"""Config and options flow for the Minecraft Broker."""

from __future__ import annotations

import logging
import re
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
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    BrokerAuthError,
    BrokerClient,
    BrokerConnectionError,
    BrokerError,
    is_secure_broker_url,
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
_INSTANCE_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class InstanceValidationError(ValueError):
    """Raised when the configured broker instance list is invalid."""


def _parse_instances(raw: str) -> list[str]:
    instances: list[str] = []
    seen: set[str] = set()
    for item in (raw or "").split(","):
        instance = item.strip()
        if not instance:
            continue
        if not _INSTANCE_LABEL_RE.fullmatch(instance) or instance in seen:
            raise InstanceValidationError
        instances.append(instance)
        seen.add(instance)
    return instances


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
            try:
                instances = _parse_instances(user_input.get(CONF_INSTANCES, ""))
            except InstanceValidationError:
                errors[CONF_INSTANCES] = "invalid_instances"

            if not is_secure_broker_url(url):
                errors["base"] = "invalid_url"
            elif not errors:
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
                vol.Required(CONF_URL): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
                vol.Required(CONF_BEARER_TOKEN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_HMAC_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_INSTANCES, default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            url = user_input[CONF_URL].strip()
            bearer_token = (
                user_input.get(CONF_BEARER_TOKEN) or entry.data[CONF_BEARER_TOKEN]
            )
            hmac_key = user_input.get(CONF_HMAC_KEY) or entry.data[CONF_HMAC_KEY]
            try:
                instances = _parse_instances(user_input.get(CONF_INSTANCES, ""))
            except InstanceValidationError:
                errors[CONF_INSTANCES] = "invalid_instances"

            if not is_secure_broker_url(url):
                errors["base"] = "invalid_url"
            elif not errors:
                if url != entry.unique_id:
                    await self.async_set_unique_id(url)
                    self._abort_if_unique_id_configured()
                try:
                    await _validate(
                        self.hass,
                        url,
                        bearer_token,
                        hmac_key,
                    )
                except BrokerAuthError:
                    errors["base"] = "invalid_auth"
                except BrokerConnectionError:
                    errors["base"] = "cannot_connect"
                except BrokerError:
                    errors["base"] = "unknown"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=url,
                        data={
                            CONF_URL: url,
                            CONF_BEARER_TOKEN: bearer_token,
                            CONF_HMAC_KEY: hmac_key,
                        },
                        options={
                            CONF_INSTANCES: instances,
                            CONF_SCAN_INTERVAL: entry.options.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        },
                    )

        current_instances = ", ".join(entry.options.get(CONF_INSTANCES, []) or [])
        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=entry.data[CONF_URL]): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
                vol.Optional(CONF_BEARER_TOKEN, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_HMAC_KEY, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_INSTANCES, default=current_instances): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
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
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                instances = _parse_instances(user_input.get(CONF_INSTANCES, ""))
            except InstanceValidationError:
                errors[CONF_INSTANCES] = "invalid_instances"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_INSTANCES: instances,
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
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
