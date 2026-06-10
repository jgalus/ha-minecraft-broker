"""Constants for the Minecraft Broker integration."""

from __future__ import annotations

DOMAIN = "minecraft_broker"

# Config entry keys.
CONF_URL = "url"
CONF_BEARER_TOKEN = "bearer_token"
CONF_HMAC_KEY = "hmac_key"
CONF_INSTANCES = "instances"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 60  # seconds
DEFAULT_TIMEOUT = 120  # seconds; start-server waits for the VM to boot

# Broker actions (see docs/automation/API.md).
ACTION_START_SERVER = "start-server"
ACTION_STOP_SERVER = "stop-server"
ACTION_SERVICE_START = "service-start"
ACTION_SERVICE_STOP = "service-stop"
ACTION_SERVICE_RESTART = "service-restart"
ACTION_STATUS = "status"

ALL_ACTIONS = [
    ACTION_START_SERVER,
    ACTION_STOP_SERVER,
    ACTION_SERVICE_START,
    ACTION_SERVICE_STOP,
    ACTION_SERVICE_RESTART,
    ACTION_STATUS,
]

# Service names (the "service-" prefix is not valid in a HA service id).
SERVICE_START_SERVER = "start_server"
SERVICE_STOP_SERVER = "stop_server"
SERVICE_SERVICE_START = "service_start"
SERVICE_SERVICE_STOP = "service_stop"
SERVICE_SERVICE_RESTART = "service_restart"
SERVICE_REFRESH = "refresh"

SERVICE_ACTION_MAP = {
    SERVICE_START_SERVER: ACTION_START_SERVER,
    SERVICE_STOP_SERVER: ACTION_STOP_SERVER,
    SERVICE_SERVICE_START: ACTION_SERVICE_START,
    SERVICE_SERVICE_STOP: ACTION_SERVICE_STOP,
    SERVICE_SERVICE_RESTART: ACTION_SERVICE_RESTART,
}

ATTR_INSTANCE = "instance"

# Label used for the unnamed/default single-instance unit.
DEFAULT_INSTANCE_LABEL = "default"
