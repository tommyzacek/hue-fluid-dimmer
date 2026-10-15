# User guides

[Čeština](../cs/README.md) | [Slovenština](../sk/README.md) | [English](../en/README.md)

| What you want to configure | Guide |
| --- | --- |
| Installation, shared conditions, Adaptive Lighting and polling | [Bridge and shared settings](bridge.md) |
| Tap Dial wheel and its four buttons | [Dial](dial.md) |
| A single-button controller | [Button](button.md) |
| Dimmer v2 with ON/OFF, +, − and HUE buttons | [Dimmer](dimmer.md) |
| Motion lighting, time periods and shutdown | [Motion](motion.md) |
| Actions, brightness, color and holding a button | [Shared button actions](akce-tlacitek.md) |

## Before you start

Hue Reconfigo requires Home Assistant **2026.10.1 or newer**, a Hue Bridge with API v2 and the configured official **Philips Hue** integration. It does not replace its devices or entities. Its panel is installed automatically and is available to HA administrators.

**Adaptive Lighting is an optional integration from HACS**, not part of the official Hue integration. Hue Reconfigo works without it. If you use it, enable [cooperation in Bridge settings](bridge.md#adaptive-lighting-cooperation).

Open **Hue Reconfigo → your Bridge → controller group → device** in the sidebar. New controllers start disabled. Settings take effect when you submit the form.

Set accessories managed by Hue Reconfigo to **“Configure in another app”** in the Hue app so Hue does not control them at the same time. Disable any blueprints or automations using the same inputs as well. Two independent systems may otherwise send conflicting brightness, color or power commands. Keep the official Philips Hue integration in Home Assistant enabled.

After an update, restart HA and refresh the browser to load the new forms. The HA profile language selects Czech, Slovak or English as the fallback. These guides use English field names.

## Recommended first test

Start with one controller and one light. Check on, off and regulation, then add light groups and other gestures. For Motion, test the complete cycle, including leaving, final dimming and returning during it. Judge smoothness by looking at the light: HA may already display the target value while a transition is still running.
