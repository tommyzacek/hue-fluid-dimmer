# v0.5.0 — Dial routing, smooth percentage controls and redesigned settings

This release combines the changes tested internally since v0.1.8.

- Button 1's short-press targets are the main dial targets. Separate dial target selection is removed.
- Buttons 2–4 can temporarily assign their short-press targets to the dial using the long-press **Dial** action. It returns after 5 seconds without rotation or 5 seconds after the last movement.
- Fan and number entities support dial control, held regulation, and button actions: off/on, off/previous percentage, or off/configured percentage.
- Long-press continuous regulation starts upward, pauses at maximum for one repeat, then reverses. Release stops further commands.
- Native Hue lights use relative dimming and a stop command during held regulation; other percentage targets use HA services.
- Custom dial settings have **Lights** and **Other entities** headings with independent sensitivity and transition/ramp fields. Balanced fan/number ramp is 0.75 seconds; preset light timing is unchanged.
- Optional experimental adaptive transitions follow report cadence and discard the old goal on direction reversal. Disabled by default; only applies to the Custom profile.
- Previous nonzero levels are saved for explicit restore actions.
- Button multiclick recognition uses a 350 ms Bridge-timestamp interval. Short-only actions do not wait for additional clicks.

Existing main dial targets migrate into button 1's short-press targets only when button 1 has no short assignment. Temporary routing is not persisted and resets on reload. Controller configuration remains in the integration, without duplicate devices or helper entities.

Physical tests covered Tap Dial rotary control, held dimming on a Hue light and number-based PWM fan control. Other device capabilities vary. A recurring external brightness change to approximately 8% is under investigation; no cause or fix is claimed in this release.

Requires Home Assistant 2026.10.1 or newer and its configured official Hue integration. After updating in HACS, restart Home Assistant and refresh the browser to load the changed form labels.
