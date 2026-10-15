# Motion

[Čeština](../cs/motion.md) | [Slovenčina](../sk/motion.md) | [English](../en/motion.md)

[All guides](README.md) · [Bridge and Adaptive Lighting](bridge.md)

Motion turns selected lights on when motion is detected, then off after a configured absence period. Motion/illuminance come from the official Hue integration; no fast motion-sensor polling is added.

## First setup

1. Open **Hue Reconfigo → Bridge → Motion → your sensor**.
2. Select target lights or a group.
3. Configure light and motion sensitivity.
4. In **All day**, set brightness, color and the no-motion timeout.
5. Choose the ending style and behavior with other controls.
6. Disable competing Hue lighting rules for this sensor, enable control in our form and save.

Keep the official sensors and Hue integration available. The form warns if the official motion or illuminance sensor switch is off. Disabling our control does not disable the official sensor.

## Light and motion sensitivity

| Field | Meaning |
| --- | --- |
| **Light sensitivity** | New light activation is permitted below the selected illuminance. The range ends at 650 lx; the next endpoint **∞** removes the illuminance restriction. |
| **Current illuminance** | Live measurement and threshold result ON/OFF. This is the light-condition result; Do not disturb, a shared condition or disabled control can still block activation. |
| **Motion sensitivity** | Three positions Low / Medium / High adjust the physical sensor's sensitivity. |

For a finite threshold, the measurement must be valid and lower than the threshold. Equality does not permit activation. Disabled/unavailable illuminance does not permit new activation with a finite threshold. Already-lit lights may still enter a cycle and later switch off according to policy.

The illuminance threshold is evaluated locally; no native Bridge illuminance rule is rewritten. Motion sensitivity is written to Bridge when saving an enabled configuration, so it can affect detection used elsewhere too.

## Dedicated times

A single period is **All day** with no editable start. Adding a period partitions the day: specify each start and the next period supplies its end. The last wraps past midnight to the first. Times use HA local time and must be unique.

| Example period | Brightness and color | No-motion timeout |
| --- | --- | --- |
| 07:00–23:00 | 80%, white 4000 K | 5 minutes |
| 23:00–07:00 | 15%, white 2300 K | 1 minute |

Each period has its own brightness, color, timeout, optional target override and **Do not disturb**. Sensitivities, ending style and controller-intervention settings are global to this Motion.

**Do not disturb** prevents new cycles. A cycle started in a previous period finishes with its original settings, including motion extensions and recovery during final dimming. Crossing a period boundary does not itself change lit lights.

### Startup brightness and color

- **Brightness → Configured %** sends the selected level.
- **Brightness → Previous state** restores saved brightness from before its own final dimming. This prevents repeated 100 → 50 → 25% reductions across cycles. Without a saved value, no brightness is sent.
- **Color → Leave unchanged** sends no color. Other choices are white temperature and custom color for supported lights.

Brightness memory does not restore color and is not a history of all external changes. Changes during a cycle are reflected in the snapshot before final dimming. A newer external off-to-on activation invalidates the old saved brightness so a subsequent activation does not overwrite it with an older value. Color is configured independently.

## Cycle and timeout

The first accepted detection starts a cycle. Motion performs startup according to its already-lit policy. **The absence timer starts only when the sensor reports no motion.** Continuous motion does not let this timer expire and switch lights off.

New motion interrupts the timer. After motion clears again, the full timeout starts again. Ordinary renewal does not repeatedly apply startup brightness/color. If final dimming has begun, it restores the saved baseline brightness.

The slider offers **1–10 minutes in half-minute increments**, then whole minutes up to **60 minutes**. Saving a changed Motion configuration cancels the old cycle; its previous countdown is not carried into the new settings.

### Soft ending

It starts in the final **30 seconds**. Each light uses its actual brightness at the start of dimming.

| Style | Final 30 seconds |
| --- | --- |
| Smooth dimming to 50% | Takes 30 s to reach half the baseline, then switches off. |
| Smooth fade to off | Gradually fades toward zero over 30 s. |
| Quick dimming to 50% and off | Takes 2 s to reach half, waits, then switches off at timeout. |

Example: Motion starts at 100%, you reduce to 60% during the cycle. The ending goes to **30%**, not 50%. Renewed motion restores **60%**.

Startup and recovery use **0.5 s** transitions; final off uses **2 s**. With soft ending disabled, brightness remains until timeout, then off is sent with that transition.

Hue may immediately report target brightness/off to HA while the physical transition is still running. HA state/history therefore is not a measurement of instantaneous physical brightness. The integration does not replace that state with an estimated value.

## Lights already on when you arrive

These two fields apply only to lights on before the cycle started. Members of a group may therefore be treated differently.

| Field | Option | Result |
| --- | --- | --- |
| On the first motion detection | Apply brightness and color from Dedicated times | Applies the current period's settings at startup, if permitted by the light condition. |
| On the first motion detection | Keep current brightness and color | Keeps the appearance and includes the light in the cycle. |
| After the no-motion timeout | Turn these lights off too | Includes previously-lit lights in automatic shutdown. |
| After the no-motion timeout | Leave them on | Does not apply ending dimming/off to previously-lit lights. |
| After the no-motion timeout | Restore brightness and color from arrival | Restores the captured original appearance at the end. |

Example: the lamp is already at 40% and the ceiling is off. Keep current brightness/color + Leave them on preserves the lamp at 40%, turns the ceiling on, then switches off only the ceiling.

## Controller intervention

**Only controllers configured in Hue Reconfigo count as manual intervention. Changes from apps or other automations do not.** External changes can affect the current brightness used for final dimming, but do not themselves invoke the handover policies below.

### Should Motion switch off after a manual brightness or color change?

| Option | Example: Motion controls lamp and ceiling; you adjust the lamp |
| --- | --- |
| **Yes, all lights** | The lamp change remains. The timer continues; both turn off according to other policies. Ordinary subsequent motion does not reapply startup brightness/color. |
| **No, none of the lights** | The whole current Motion selection is handed to the user. The ceiling does not change brightness, but no longer switches off automatically either. |
| **Only lights that were not manually controlled** | The lamp is handed over; the ceiling still switches off with the cycle. |

These options do not select brightness/color at intervention. They determine which lights Motion continues controlling. The separate policy for lights already on at arrival still applies.

Handed-over lights return to full control only after **being switched off, completion of the original cycle and a new motion detection**. There is no return timer. Elapsed time or sensor inactivity alone does not take them back. While the sensor reports motion, the original cycle may not yet have finished its absence countdown.

### When I turn lights off with a controller

| Option | Result for the lights just switched off |
| --- | --- |
| **The next motion detection may turn them on again immediately** | A new detection may readopt them into the running cycle. |
| **Keep them off until the current cycle ends** | Further motion cannot turn them on in this cycle. A new cycle can take them back. |

“Immediately” means the next new motion event. A sensor continuously reporting motion does not cause the integration to invent another detection. This applies to the actual switched-off lights, not automatically the entire room.

## Three practical setups

| Goal | Already lit on arrival | After timeout | After manual change |
| --- | --- | --- | --- |
| Hallway: Motion handles everything | Apply period settings | Turn these lights off too | Yes, all lights |
| Living room: respect an existing lamp | Keep current brightness/color | Leave them on | Only lights not manually controlled |
| Room: manual change takes over all lighting | As desired | As desired | No, none of the lights |

For absence blocking, use the [shared entity condition](bridge.md#block-control-by-entity) and select Motion. It is independent of and applies across all periods.
