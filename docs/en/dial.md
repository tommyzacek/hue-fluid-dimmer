# Tap Dial

[Čeština](../cs/dial.md) | [Slovenčina](../sk/dial.md) | [English](../en/dial.md)

[All guides](README.md) · [Shared button actions](akce-tlacitek.md)

Tap Dial has a wheel and four buttons. The wheel adjusts a percentage value, while buttons have separate actions for each gesture.

## Main wheel targets

Open **Hue Fluid Dimmer → Bridge → Dial → your controller**. By default, the wheel uses button 1's short-press targets. To control a whole room with the wheel but only part of it with button 1, enable the wheel's independent target selection and choose the larger group.

Main targets must support regulation: lights, fans or suitable number entities. Scripts have no continuous percentage value and cannot be wheel targets. Use lights or compatible other percentage entities in one selection.

## Speed and smoothness

| Profile | Light sensitivity | Light transition | Other entity sensitivity | Other entity ramp |
| --- | --- | --- | --- | --- |
| Gentle | 1.2 | 1 s | 0.75 | 1 s |
| Balanced | 2.4 | 1 s | 1.5 | 0.75 s |
| Swift | 4.8 | 0.5 s | 3 | 0.5 s |
| Custom | Custom value | Custom value | Custom value | Custom value |

Sensitivity is the base change in percentage points per 15 Bridge-reported steps. It is not a guaranteed change per physical detent.

All three presets enable adaptive behavior: slow rotation supports fine adjustment, fast rotation larger changes. Custom exposes separate **Lights** and **Other entities** sections, each with sensitivity and transition/ramp, plus an adaptive switch. Custom values remain saved when selecting a preset.

Higher sensitivity covers more of the range with the same movement. Shorter transitions reach targets sooner but may expose stepping. Start with Balanced and change one value at a time. These settings affect command response, not arrival latency of controller events.

Lights use transitions supported by their integration; other entities use software ramps via HA services. Actual steps and smoothness depend on the device. Reversing rotation discards pending future targets in the old direction. With adaptive behavior, transition settings are not a guaranteed fixed duration for every change.

## Temporary wheel takeover

**Any gesture on buttons 2, 3 or 4** can temporarily take over the dial. Select targets directly for that gesture. The same button's short press may remain disabled or control something else.

Example:

1. The main wheel controls kitchen lights.
2. Enable double press on button 2, select a fan and the Dial takeover action.
3. Double press redirects the wheel to the fan. It does not also invoke a regular button power action.
4. Rotation changes fan output using **Other entities** settings.
5. After **5 seconds since the last rotation**, the wheel returns to its main targets. If you never rotate after takeover, it returns **5 seconds after takeover**.

Takeover does not rewrite permanent settings or restore the fan's previous output. It changes only what the wheel controls temporarily. Releasing the button does not end routing; the timeouts do. This action is unavailable on button 1 and on standalone Button or Dimmer controllers.

Other button actions, appearance and held regulation are covered in [shared actions](akce-tlacitek.md). See [Bridge settings](bridge.md) for polling and shared conditions.
