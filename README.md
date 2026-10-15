# Hue Reconfigo

[Čeština](README.cs.md) | [Slovenčina](README.sk.md) | [English](README.md)

*Home Assistant control hub for Hue Tap Dial, Dimmer, Smart Button and Motion sensors.*

A Home Assistant companion for Philips Hue **Tap Dial**, **Smart Button**, **Dimmer v2** and **Motion sensors**. Configure actions, targets, brightness and color directly in the integration, without per-controller automations or duplicate controller entities.

Requires **Home Assistant 2026.10.1 or newer**, a Hue Bridge with API v2 and the configured official **Philips Hue** integration. This project is independent of Signify and Home Assistant. Documentation follows the latest development; use the release notes for the scope of a specific installed version.

The official **Philips Hue** integration is required. **Adaptive Lighting** is a separate, optional custom integration installed through **HACS**. If you use it, enable cooperation in Hue Reconfigo’s Bridge settings to report manual brightness/color control. Hue Reconfigo works without Adaptive Lighting.

The integration was previously named **Hue Fluid Dimmer**. Its technical domain and component directory are now `hue_reconfigo`. Existing installations must complete the [domain migration](docs/en/domain-migration.md) before restarting with this version. Hue Bridge pairing is preserved.

## User guides

| Group | Guide |
| --- | --- |
| Bridge | [Installation, shared conditions, Adaptive Lighting and polling](docs/en/bridge.md) |
| Dial | [Wheel profiles, four buttons and temporary takeover](docs/en/dial.md) |
| Button | [Short/long press, double and triple press](docs/en/button.md) |
| Dimmer | [ON/OFF, +, − and HUE on Dimmer v2](docs/en/dimmer.md) |
| Motion | [Time periods, light sensitivity, timeout and manual intervention](docs/en/motion.md) |
| Shared actions | [Power, brightness, color, held regulation, fans and scripts](docs/en/akce-tlacitek.md) |

Start with [Before you start](docs/en/README.md#before-you-start). Each guide includes examples and explains how the options interact.

## Quick installation

1. Add `https://github.com/tommyzacek/hue-reconfigo` to HACS custom repositories as an **Integration**.
2. Download a release and restart Home Assistant.
3. Add **Hue Reconfigo** in **Settings → Devices & services**, then select your existing Hue Bridge.
4. In the Hue app, set managed accessories to **Configure in another app**. Disable competing automations for the same inputs; keep the official Hue integration enabled.
5. Open **Hue Reconfigo** in the sidebar as an administrator. Select a controller, configure its targets/actions and enable control. The Bridge gear opens shared settings. Refresh the browser after updates.

For manual installation, copy `custom_components/hue_reconfigo` into your HA configuration's `custom_components` directory and restart. The sidebar panel is included; no separate dashboard installation is needed.

## Supported devices

| Type | Scope |
| --- | --- |
| Tap Dial | Discovered rotary resources and four buttons |
| Smart Button | ROM001, RDM003, RDM005 |
| Dimmer v2 | RWL022; Dimmer v1 and wall modules are outside scope |
| Hue Motion | Discovered motion services; official HA sensor entities required |

New controllers start disabled. Lights/groups, fans, suitable number entities and one script can be used as button targets; regulation requires percentage-capable targets. Scene cycling is not provided directly. RDM005 mapping is not a claim of physical validation of every feature.

## Development and limitations

The UI supports Czech, Slovak and English, selected by the HA profile. Other languages fall back to English.

Native Hue transitions may report the target state before the physical fade finishes. Smoothness and response depend on devices and network conditions. Synthetic tests do not replace physical verification.

See [technical notes and development](docs/development.md) for testing, connection details and the historical Adaptive Lighting toggle observation. CI runs tests, Ruff, hassfest and HACS validation.
