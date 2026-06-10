"""Button platform for the Minecraft Broker."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BrokerError
from .const import (
    ACTION_SERVICE_RESTART,
    ACTION_SERVICE_START,
    ACTION_SERVICE_STOP,
    ACTION_START_SERVER,
    ACTION_STOP_SERVER,
    CONF_INSTANCES,
    DOMAIN,
)
from .coordinator import BrokerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrokerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = [
        BrokerButton(coordinator, entry, "start_server", "Start server",
                     "mdi:play", ACTION_START_SERVER, None),
        BrokerButton(coordinator, entry, "stop_server", "Stop server",
                     "mdi:stop", ACTION_STOP_SERVER, None),
    ]
    for instance in entry.options.get(CONF_INSTANCES, []) or []:
        entities.extend(
            [
                BrokerButton(coordinator, entry, f"restart_{instance}",
                             f"Restart {instance}", "mdi:restart",
                             ACTION_SERVICE_RESTART, instance),
                BrokerButton(coordinator, entry, f"start_{instance}",
                             f"Start {instance}", "mdi:play-circle",
                             ACTION_SERVICE_START, instance),
                BrokerButton(coordinator, entry, f"stop_{instance}",
                             f"Stop {instance}", "mdi:stop-circle",
                             ACTION_SERVICE_STOP, instance),
            ]
        )
    async_add_entities(entities)


class BrokerButton(CoordinatorEntity[BrokerCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrokerCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
        action: str,
        instance: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._action = action
        self._instance = instance
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_button_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Minecraft Broker",
            manufacturer="Minecraft Broker",
        )

    async def async_press(self) -> None:
        from homeassistant.exceptions import HomeAssistantError

        try:
            await self.coordinator.client.async_call(self._action, self._instance)
        except BrokerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_refresh_after_action()
