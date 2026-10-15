# Shared button actions

[Čeština](../cs/akce-tlacitek.md) | [Slovenčina](../sk/akce-tlacitek.md) | [English](../en/akce-tlacitek.md)

[All guides](README.md) · [Button](button.md) · [Dimmer](dimmer.md) · [Dial](dial.md)

Short press, long press, double press and triple press have individual switches and settings. Available actions depend on the controller, gesture and targets. A disabled gesture performs no action.

## Light actions

| Action | Result |
| --- | --- |
| **Turn on / off** | If any selected light is on, turns the selection off. Otherwise turns it on using the configured brightness and color. |
| **Turn on only** | Always turns on and applies brightness/color, even to an already-lit light. Repeating it does not turn the light off. |
| **Turn off only** | Always turns off. Brightness and color settings do not apply. |
| **Continuous regulation while held** | Long press only: regulates while held; release stops it. |

Two-color example: short press uses Turn on / off, 70%, 4000 K; double press uses Turn on only, 30%, 2300 K. Double press changes the appearance of a lit light. With Turn on / off on both gestures, it would turn the light off instead.

### Brightness and color are independent

| Field | Option | Meaning |
| --- | --- | --- |
| Brightness | **Previous state** | Uses saved brightness. After Motion's final dimming, restores pre-dimming brightness. Without a saved value, sends no brightness and leaves startup to the light or its integration. |
| Brightness | **Configured %** | Sends the selected brightness when turning on. |
| Light color | **Leave unchanged** | Sends neither color nor white temperature. |
| Light color | **White temperature** | Sends kelvins within each light's capabilities. The slider selects in increments of 100 K. |
| Light color | **Custom color** | Sends the selected color to supported lights. |

Previous state does not restore a whole scene or color. The integration remembers brightness when it turns lights off and before its own final dimming. It is not a universal history of every change in every app. Unsupported color settings are not sent to a light.

With [AL cooperation](bridge.md#adaptive-lighting-cooperation) enabled, explicit brightness/color settings are marked as manual parameters. Leaving color unchanged does not itself determine whether AL will subsequently change it.

## Action targets

Button and Dimmer have **Default lights / devices** at the top. Gestures use these automatically. Enable **Use different devices for this action** to choose exceptions. Disabling that override restores defaults and discards the old custom selection.

Tap Dial has targets for each gesture directly. Temporary wheel takeover uses the targets of the exact gesture that invoked it.

Targets can be lights/groups, `fan` entities, `number` entities or one script. Direct scene selection/cycling is not provided; a script can implement custom sequences. Do not mix different entity domains in a regular action. Regulation requires compatible percentage-controllable targets.

## Fans and number entities

These targets retain percentage-based toggle variants:

| Option | When turning on |
| --- | --- |
| Turn on / off | A fan uses its normal turn-on behavior; a number target goes to its upper bound. |
| Off / previous percentage | Restores a nonzero level saved when the integration switched it off. Without a saved value, a fan turns on normally; a number target does not guess an output and logs a warning. |
| Off / configured percentage | Applies the configured percentage. |
| Turn on only | Applies the configured percentage even if already running. |
| Turn off only | Sets zero percent of the range. |

For `number`, 0–100% maps to its `min`–`max` range and respects `step`. **0% therefore means the entity's minimum, which is not necessarily physical off.** For a PWM fan, verify that minimum really means stopped. A fan may support fewer than a hundred actual speeds.

## Holding a button

**Continuous regulation while held** begins when a long press is recognized; release stops it. Direction is selected at the beginning:

- below 30%: up;
- above 60%: down;
- between those values: opposite the previous hold; first hold goes up.

At an endpoint, it waits for release; it does not reverse during the same hold. Dimmer + and − have fixed directions. Hue lights may use direct relative dimming with a stop command; other devices use HA services. Visible stopping delay also depends on the device and connection.

## Double and triple presses

Without enabled multiclick gestures, a short press is evaluated on release without waiting for another press. When they are enabled, the integration must wait for possible continuation. Recognition uses a **350 ms** interval and Bridge timestamps; delivery can add latency. Press naturally and quickly; there is no need to measure exact gaps.

## Scripts

Select one `script` entity. A normal action calls `script.turn_on`; a second press does not toggle it off like a light. Repeated starts follow the script's mode (`single`, `restart`, `queued`, `parallel`). **Turn off only** calls `script.turn_off` and can interrupt pending steps. Account for this when controlling a lock or another important action. Turn on only is a clear choice for triggering a script.
