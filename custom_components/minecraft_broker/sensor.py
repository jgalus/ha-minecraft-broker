"""Sensor platform for the Minecraft Broker."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_INSTANCES, DOMAIN
from .coordinator import BrokerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrokerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        VmPowerStateSensor(coordinator, entry),
        PublicIpSensor(coordinator, entry),
    ]
    for instance in entry.options.get(CONF_INSTANCES, []) or []:
        entities.append(InstanceStatusSensor(coordinator, entry, instance))
    async_add_entities(entities)


class _BaseSensor(CoordinatorEntity[BrokerCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BrokerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Minecraft Broker",
            manufacturer="Minecraft Broker",
            entry_type=None,
        )


class VmPowerStateSensor(_BaseSensor):
    _attr_translation_key = "vm_power_state"
    _attr_icon = "mdi:server"

    def __init__(self, coordinator: BrokerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_vm_power_state"
        self._attr_name = "VM power state"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("vm_power_state")

    @property
    def extra_state_attributes(self) -> dict:
        return {"public_ip": self.coordinator.data.get("public_ip")}


class PublicIpSensor(_BaseSensor):
    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator: BrokerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_public_ip"
        self._attr_name = "Public IP"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("public_ip")


class InstanceStatusSensor(_BaseSensor):
    _attr_icon = "mdi:minecraft"

    def __init__(
        self, coordinator: BrokerCoordinator, entry: ConfigEntry, instance: str
    ) -> None:
        super().__init__(coordinator, entry)
        self._instance = instance
        self._attr_unique_id = f"{entry.entry_id}_instance_{instance}"
        self._attr_name = f"Instance {instance}"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("instances", {}).get(self._instance, "unknown")
