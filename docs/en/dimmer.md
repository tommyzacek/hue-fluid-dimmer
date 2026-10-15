# Dimmer v2

[Čeština](../cs/dimmer.md) | [Slovenčina](../sk/dimmer.md) | [English](../en/dimmer.md)

[All guides](README.md) · [Shared button actions](akce-tlacitek.md)

This guide covers **Hue Dimmer v2, model RWL022**. Dimmer v1 and wall modules are outside this support scope.

| Position | Button | Typical purpose |
| --- | --- | --- |
| 1, top | ON/OFF | Power |
| 2 | + | Increase brightness |
| 3 | − | Decrease brightness |
| 4, bottom | HUE | Another configured action |

The printed symbol does not lock a button to one function. Configure its supported gestures in the form. HUE does not automatically cycle scenes here.

## Basic setup

Open **Hue Fluid Dimmer → Bridge → Dimmer → your controller**, select default targets and configure the buttons. New configurations prepare a short step and long regulation for + and −. Check these before saving; previously saved choices may differ.

| Button and gesture | Suggested action | Result |
| --- | --- | --- |
| ON/OFF short | Turn on / off | Turns on with selected brightness/color, or off. |
| + short | Increase by 10 percentage points | Adds 10 percentage points. |
| + long | Continuous regulation while held | Increases while held. |
| − short | Decrease by 10 percentage points | Subtracts 10 percentage points. |
| − long | Continuous regulation while held | Decreases while held. |
| HUE short | Turn on only | For example, applies evening brightness and warm white. |

Held regulation on + and − uses fixed directions, not the 30/60% thresholds. Stepping is available on short presses of these middle buttons. Other held-regulation gestures use the shared direction rules.

## A different target for HUE

Enable **Use different devices for this action** for HUE and choose a fan or one script, for example. Other buttons still use the default lights. Double/triple presses can be separated in the same way.

If rapid ON/OFF presses change the light's colors, check that the Dimmer is no longer assigned in Hue. Native actions can cycle scenes concurrently. AL may also change the light; enable [cooperation](bridge.md#adaptive-lighting-cooperation) in Bridge settings if needed.

Brightness, color, one-way power and scripts are covered in the [shared guide](akce-tlacitek.md).
