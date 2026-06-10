"""Status polling coordinator for the Minecraft Broker."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BrokerClient, BrokerError
from .const import ACTION_STATUS, DEFAULT_INSTANCE_LABEL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BrokerCoordinator(DataUpdateCoordinator[dict]):
    """Polls the broker ``status`` action and exposes the normalized result.

    ``data`` shape::

        {
          "vm_power_state": "running" | "deallocated" | ...,
          "public_ip": "x.x.x.x" | None,
          "instances": { "survival": "active" | "inactive" | "unknown", ... },
        }
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BrokerClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict:
        try:
            resp = await self.client.async_call(ACTION_STATUS)
        except BrokerError as err:
            raise UpdateFailed(str(err)) from err
        return _normalize(resp)

    async def async_refresh_after_action(self) -> None:
        """Request a refresh following a control action."""
        await self.async_request_refresh()


def _normalize(resp: dict) -> dict:
    instances = resp.get("instances") or {}
    if not isinstance(instances, dict):
        instances = {}
    # Defensive: tolerate either bare labels or unit names as keys.
    normalized = {_label(key): value for key, value in instances.items()}
    return {
        "vm_power_state": resp.get("vm_power_state", "unknown"),
        "public_ip": resp.get("public_ip"),
        "instances": normalized,
        "message": resp.get("message"),
    }


def _label(key: str) -> str:
    name = key[: -len(".service")] if key.endswith(".service") else key
    if name == "minecraft":
        return DEFAULT_INSTANCE_LABEL
    if name.startswith("minecraft-"):
        return name[len("minecraft-"):]
    return name
