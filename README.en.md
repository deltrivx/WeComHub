# WeComHub

[简体中文](README.md) | **English** | [Release Index](RELEASES.md)

[![Latest Release](https://img.shields.io/github/v/release/deltrivx/WeComHub?display_name=tag&sort=semver&label=latest)](https://github.com/deltrivx/WeComHub/releases/latest)
[![Unraid](https://img.shields.io/badge/Unraid-6.9%2B-F15A2C?logo=unraid&logoColor=white)](https://unraid.net/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

WeComHub is an Unraid plugin that turns WeCom (WeChat Work) into a two-way channel for your server: system notifications go out, and text commands come back in.

> Plugin ID: `wecom.hub` · Minimum Unraid version: **6.9.0**

## Features

- Configuration lives in **Settings -> Notification -> Notification Agents** — same entry point as the built-in agents, no env files, no edits to `/boot/config/go`.
- System notifications (array, disks, containers, uptime, ...) are relayed to a WeCom application.
- Inbound commands: read-only queries (array, containers, load, disks) and restricted container restarts.
- Minimum notification level filter: `normal` / `warning` / `alert`.
- Starts at boot through the array-started event hook invoking `/etc/rc.d/rc.WeComHub`.
- Every `plg` / `txz` archive is built by GitHub Actions and published to a Release.

## Why a relay is required

WeCom only accepts API calls from IPs listed in the corporate "trusted IP" allowlist. A fixed, stable public IP is therefore required, and the relay service provides it.

WeComHub hands notifications to the relay; the Unraid host never calls WeCom directly.

## Architecture

```text
WeCom  <->  Relay service (fixed public IP)  <->  WeComHub (Unraid)
                                                   |-- notify agent  (outbound)
                                                   +-- command service (inbound)
```

## Installation

In the Unraid WebGUI open **Plugins -> Install Plugin** and paste:

```text
https://raw.githubusercontent.com/deltrivx/WeComHub/main/wecom.hub.plg
```

Then open **Settings -> Notification -> Notification Agents**, find **WeComHub**, and fill in:

| Setting | Placeholder | Notes |
| --- | --- | --- |
| Relay Host | `RELAY_HOST` | Domain or IP of your relay |
| Relay Port | `RELAY_PORT` | Default `8181` |
| Push Token | `RELAY_PUSH_TOKEN` | Shared secret with the relay |
| Minimum Importance | `normal` | Lowest notification level to forward |

All values above are placeholders. Use your own; the repository never contains real credentials.

## Data and security

- Config: `/boot/config/plugins/WeComHub/wecom.hub.cfg` (mode `0600`).
- The push token is never echoed back to the page or written to logs.
- The command service only runs whitelisted commands. `restart` is limited to the `RESTART_ALLOW_PREFIX` prefix and validates the container name charset.
- Token comparison is constant-time.

## Documentation and support

- [Project overview](ABOUT.md)
- [Changelog](CHANGELOG.md)
- [Configuration](docs/configuration.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Troubleshooting and support](SUPPORT.md)

## License

Source code is [MIT](LICENSE). Documentation and visual assets are [CC BY-NC-SA 4.0](LICENSE-ASSETS.md). Third-party names and trademarks remain subject to their respective rights; see [NOTICE](NOTICE).
