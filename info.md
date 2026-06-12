# Minecraft Broker

Control your private Azure Minecraft server from Home Assistant — securely.

Start/stop the VM as whole-VM actions and start/stop/restart named Minecraft
instances by calling a least-privilege **broker** (an Azure Function). Home
Assistant holds only a narrow, revocable bearer token + HMAC key — never Azure
credentials.

**Provides**
- Sensors: VM power state, public IP, per-instance status.
- Buttons: Start Server, Stop Server (whole VM), and per-instance Restart / Start / Stop.
- Services: `minecraft_broker.start_server`, `stop_server`, `service_start`,
  `service_stop`, `service_restart`, `refresh`.

The integration computes the broker's required HMAC-SHA256 + timestamp + nonce
signature natively — no `shell_command` or external scripts needed.

See the [README](https://github.com/jgalus/ha-minecraft-broker) for setup.
