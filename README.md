# Minecraft Broker — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Control your private Azure Minecraft server from Home Assistant — **securely**. Start
and stop the VM, and start/stop/restart named Minecraft instances, by calling a
least-privilege **broker** (an Azure Function). Home Assistant stores only a narrow,
revocable bearer token + HMAC key — **never** Azure credentials.

The integration computes the broker's required `HMAC-SHA256 + timestamp + nonce`
signature **natively in Python**, so there is no `shell_command`, no external signer
script, and nothing to install on the host beyond this integration.

> Broker + API contract: see the server project's `docs/automation/API.md` and
> `broker/README.md`.

## What you get

**Sensors**
- `sensor.minecraft_broker_vm_power_state` — `running` / `deallocated` / … (with a
  `public_ip` attribute).
- `sensor.minecraft_broker_public_ip` — the VM's public IP (or `unknown`).
- `sensor.minecraft_broker_instance_<name>` — per-instance `active` / `inactive` /
  `unknown` (one per configured instance).

**Buttons**
- Start server, Stop server (whole VM).
- Per instance: Restart, Start, Stop.

**Services** (callable from automations/scripts)
- `minecraft_broker.start_server` (optional `instance`)
- `minecraft_broker.stop_server`
- `minecraft_broker.service_start` / `service_stop` / `service_restart` (require `instance`)
- `minecraft_broker.refresh`

## Installation (HACS)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**, add
   `https://github.com/jgalus/ha-minecraft-broker` with category **Integration**.
2. Install **Minecraft Broker**, then restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → Minecraft Broker**.

### Manual installation
Copy `custom_components/minecraft_broker/` into your HA `config/custom_components/`
directory and restart.

## Configuration

The config flow asks for:

| Field | Example | Notes |
|---|---|---|
| Broker URL | `https://minecraft-broker-fn.azurewebsites.net/api/control` | Ends in `/api/control`. |
| Bearer token | `…` | The `BROKER_BEARER_TOKEN` set on the broker. |
| HMAC key | `…` | The `BROKER_HMAC_KEY` set on the broker. |
| Instances | `survival, creative` | Comma-separated; creates per-instance entities/buttons. |

Setup validates the values by issuing a `status` call. You can later change the
instance list and the **status poll interval** via the integration's **Configure**
(options) dialog.

## Security notes
- Only two secrets live in Home Assistant — both narrow and revocable. No Azure
  credentials are ever stored.
- Every request is signed (HMAC over timestamp + nonce + body) and sent over TLS; the
  broker rejects stale or replayed requests.
- To revoke access, rotate `BROKER_BEARER_TOKEN` / `BROKER_HMAC_KEY` on the broker and
  update this integration (Configure → re-enter), or remove the integration.

## Example automation

```yaml
automation:
  - alias: "Start Minecraft at 16:00 on weekends"
    trigger:
      - platform: time
        at: "16:00:00"
    condition:
      - condition: time
        weekday: [sat, sun]
    action:
      - service: minecraft_broker.start_server
        data:
          instance: survival
```

## Development / validation
- CI (`.github/workflows/validate.yml`) runs **hassfest** and the **HACS** action.
- The signing helpers in `api.py` are dependency-free and are verified to interoperate
  with the broker's own verifier.

## License
MIT — see [LICENSE](LICENSE).
