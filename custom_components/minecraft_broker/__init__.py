"""The Minecraft Broker integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BrokerClient, BrokerError
from .const import (
    ATTR_INSTANCE,
    CONF_BEARER_TOKEN,
    CONF_HMAC_KEY,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    SERVICE_ACTION_MAP,
    SERVICE_REFRESH,
    SERVICE_SERVICE_RESTART,
    SERVICE_SERVICE_START,
    SERVICE_SERVICE_STOP,
    SERVICE_START_SERVER,
    SERVICE_STOP_SERVER,
)
from .coordinator import BrokerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

_INSTANCE_REQUIRED = {
    SERVICE_SERVICE_START,
    SERVICE_SERVICE_STOP,
    SERVICE_SERVICE_RESTART,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Minecraft Broker from a config entry."""
    session = async_get_clientsession(hass)
    client = BrokerClient(
        session,
        entry.data[CONF_URL],
        entry.data[CONF_BEARER_TOKEN],
        entry.data[CONF_HMAC_KEY],
        timeout=DEFAULT_TIMEOUT,
    )
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = BrokerCoordinator(hass, entry, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            _async_unregister_services(hass)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change (instances / poll interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


def _coordinators(hass: HomeAssistant) -> list[BrokerCoordinator]:
    return list(hass.data.get(DOMAIN, {}).values())


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        return

    service_schema = vol.Schema({vol.Optional(ATTR_INSTANCE): cv.string})

    async def _handle(call: ServiceCall) -> None:
        instance = call.data.get(ATTR_INSTANCE)
        coordinators = _coordinators(hass)
        if not coordinators:
            raise HomeAssistantError("Minecraft Broker is not configured")

        if call.service == SERVICE_REFRESH:
            for coordinator in coordinators:
                await coordinator.async_request_refresh()
            return

        if call.service in _INSTANCE_REQUIRED and not instance:
            raise HomeAssistantError(
                f"Service {call.service} requires an 'instance'"
            )

        action = SERVICE_ACTION_MAP[call.service]
        # Services act on the single configured broker (the common case). If
        # multiple are configured, the first is used; call entity buttons for a
        # specific broker instead.
        coordinator = coordinators[0]
        try:
            await coordinator.client.async_call(action, instance)
        except BrokerError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_refresh_after_action()

    for service in (
        SERVICE_START_SERVER,
        SERVICE_STOP_SERVER,
        SERVICE_SERVICE_START,
        SERVICE_SERVICE_STOP,
        SERVICE_SERVICE_RESTART,
        SERVICE_REFRESH,
    ):
        hass.services.async_register(DOMAIN, service, _handle, schema=service_schema)


def _async_unregister_services(hass: HomeAssistant) -> None:
    for service in (
        SERVICE_START_SERVER,
        SERVICE_STOP_SERVER,
        SERVICE_SERVICE_START,
        SERVICE_SERVICE_STOP,
        SERVICE_SERVICE_RESTART,
        SERVICE_REFRESH,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
