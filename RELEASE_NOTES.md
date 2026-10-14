# v0.7.0 — Smart Button, Dimmer v2 and simpler controller settings

- Add model-specific setup for Smart Button ROM001/RDM003/RDM005 and Dimmer v2 RWL022. Newly discovered controllers appear as disabled configuration rows, without duplicate entities or devices.
- Simplify default targets: each Button/Dimmer action uses the controller's default devices unless **Use different devices for this action** is enabled. Turning it off removes the override. Function toggles use switches throughout.
- Remove scene selection and scene cycling. Scripts remain available for custom actions. Existing scene assignments are no longer executed; replace them with a script or a supported target.
- Continuous held regulation chooses its direction at the start: below 30% up, above 60% down, otherwise alternate from the previous hold (first up). It stops at endpoints and on release. Dimmer +/− have fixed direction and 10-point short-press steps.
- Cancel pending native Hue held commands before stopping, including on unload; prevent a delayed initial brightness read from starting a ramp after release.
- Make the tested adaptive tuning the default presets. Light sensitivities are 1.2 / 2.4 / 4.8; other entity sensitivities are 0.75 / 1.5 / 3. Balanced other-entity ramp remains 0.75 s. Every named preset enables adaptive transitions; Custom retains independent fields and its adaptive switch.
- Add Slovak translations alongside Czech and English, improve target labels, and fix the invalid heading translation keys that failed hassfest in v0.5.0.
- Align development package and integration versions at 0.7.0, and refresh documentation.

Tap Dial temporary routing still returns after 5 seconds, and short-only actions retain immediate release handling. Existing targets and custom values are preserved. New Button/Dimmer control remains experimental and requires physical validation; RDM005 has not been physically tested at the development installation.

Requires Home Assistant 2026.10.1 or newer and the official Hue integration. After updating through HACS, restart HA and refresh the browser to load the new form labels. Disable competing native Hue or automation assignments before enabling new controller actions.
