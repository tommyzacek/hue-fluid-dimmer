<p align="center">
  <img src="docs/assets/hue-reconfigo-logo.png" alt="Hue Reconfigo" width="360">
</p>

# Hue Reconfigo

[Čeština](README.cs.md) | [Slovenština](README.sk.md) | [English](README.md)

Configure Hue **Tap Dial, Smart Button, Dimmer v2 and Motion sensors** directly in Home Assistant. Set actions, brightness, color and motion behavior through forms, without YAML or separate automations for each controller. Control lights and other compatible devices with an emphasis on fast response and smooth adjustment.

<p align="center">
  <img src="docs/assets/screenshots/panel.png" alt="Hue Reconfigo sidebar panel" width="760">
</p>

Requires **Home Assistant 2026.10.1 or newer**, a **Hue Bridge with API v2** and the configured official **Philips Hue** integration.

**Adaptive Lighting is optional.** If you use it, enable cooperation in the Bridge settings so Hue Reconfigo reports manual brightness and color changes. [Connection details](docs/en/bridge.md#adaptive-lighting-cooperation).

## Quick installation

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tommyzacek&repository=hue-reconfigo&category=integration)

1. Add `https://github.com/tommyzacek/hue-reconfigo` to HACS custom repositories as an **Integration**.
2. Download a release and restart Home Assistant.
3. Add **Hue Reconfigo** in **Settings → Devices & services**, then select your existing Hue Bridge.
4. In the Hue app, set managed accessories to **Configure in another app**. Disable competing automations for the same inputs; keep the official Hue integration enabled.
5. Open **Hue Reconfigo** in the sidebar as an administrator. Select a controller, configure its targets/actions and enable control. The Bridge gear opens shared settings. Refresh the browser after updates.

After downloading and restarting Home Assistant:

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hue_reconfigo)

Manual installation: copy `custom_components/hue_reconfigo` into HA’s `custom_components` directory and restart. The sidebar panel is included.

## User guides

| Group | Guide |
| --- | --- |
| Bridge | [Installation, shared conditions, Adaptive Lighting and polling](docs/en/bridge.md) |
| Dial | [Wheel profiles, four buttons and temporary takeover](docs/en/dial.md) |
| Button | [Short/long press, double and triple press](docs/en/button.md) |
| Dimmer | [ON/OFF, +, − and HUE on Dimmer v2](docs/en/dimmer.md) |
| Motion | [Time periods, light sensitivity, timeout and manual intervention](docs/en/motion.md) |
| Shared actions | [Power, brightness, color, held regulation, fans and scripts](docs/en/akce-tlacitek.md) |

The interface and guides are available in Czech, Slovak and English. New controllers start disabled. Native Hue transitions can report the target state before a fade finishes; response and smoothness depend on your devices and network.

An independent project, not affiliated with Signify or Home Assistant. Guides follow current development; see [release notes](https://github.com/tommyzacek/hue-reconfigo/releases) for your installed version and [technical notes](docs/development.md) for limitations.
