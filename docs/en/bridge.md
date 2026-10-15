# Bridge and shared settings

[Čeština](../cs/bridge.md) | [Slovenčina](../sk/bridge.md) | [English](../en/bridge.md)

[All guides](README.md)

## Installation and opening settings

1. Add `https://github.com/tommyzacek/hue-reconfigo` to HACS as a custom repository of type **Integration**.
2. Download the desired release and restart Home Assistant. Enable pre-release visibility in HACS if you want pre-releases.
3. In **Settings → Devices & services → Add integration**, choose Hue Reconfigo and your existing Hue Bridge.
4. Open **Hue Reconfigo** in the sidebar. Controllers are grouped into Dial, Button, Dimmer and Motion.

The gear beside the Bridge name opens shared settings directly in the panel. Standard integration settings remain available in Devices & services too. The panel needs no separate installation, creates no extra Bridge or duplicate entities and adds no periodic polling itself.

## Block control by entity

This feature was created to prevent automatic lighting in an empty home. A pet, an unwanted detection or an unauthorized entry can trigger motion when turning on lights is undesirable. If HA already has an entity representing your household state, you can use it to permit Motion only while “home” and leave manual controllers working. The same approach supports other conditions without depending on one particular presence system.

Control is permitted only in specified states of the selected entity. The condition applies to the selected controller families throughout this Bridge, not just one Motion or time period.

1. Enable **Block control by entity**.
2. Choose which families should respect it: Motion, Button, Dial and Dimmer. Dial includes the wheel and its buttons.
3. Choose the **Control entity**.
4. Type exact **Allowed states**, separated by commas for multiple values.

Example: entity `sensor.household_mode`, allowed state `home`, only Motion selected. Motion can turn lights on only while the state is `home`; manual controllers still work. If your entity uses `doma` instead, enter `doma`. Use the actual, case-sensitive state from **Developer tools → States**, not a translated display label.

Any other state, `unknown`, `unavailable` or a missing entity blocks the selected controls. Returning to an allowed state does not switch anything on by itself; it permits future input. Active held regulation stops. Existing Motion cycles may finish and switch off, but blocked motion cannot extend them or restore brightness during final dimming. Official sensor reporting continues.

This condition limits integration actions. It is not a security system.

## Adaptive Lighting cooperation

**Adaptive Lighting (AL) is a separate, optional custom integration installed through HACS.** It is not part of the official Philips Hue integration and is not required by Hue Reconfigo. The official Philips Hue integration, in contrast, is required and must remain enabled.

If you use Adaptive Lighting (AL), you can enable cooperation. The integration discovers matching AL configurations and reports manual brightness/color control using `adaptive_lighting.set_manual_control`.

- The manual flag belongs to AL, not the bulb or Hue Bridge.
- Groups are expanded to known members. Only controlled lights managed by a matching AL configuration are marked; multiple matching configurations are handled separately.
- If AL manages an unexpanded group as one entity, marking only some members is unsafe. Partial operations are skipped with a log warning. Control the whole group or enable AL's `expand_light_groups` option.
- Brightness and color are distinguished where the installed AL version supports it. Older AL may pause the other component too.
- Explicit Motion startup brightness/color choices are manual parameters. Temporary final dimming uses a separate pause that is subsequently released. Restoring pre-dimming brightness alone does not request a new manual flag.

The integration does not change AL configuration or create profiles. AL determines when adaptation resumes after manual control. Hue Reconfigo also works without AL. Explicitly turning a light off cannot prevent another automation from subsequently turning it on.

## Polling mode

| Option | Behavior | When to use it |
| --- | --- | --- |
| **After first event** | Starts temporary Bridge reads after an event. Repeated REST reads do not run while idle. | Recommended economical starting point. |
| **Continuous** | Reads buttons and wheels while idle too. | When you have a reason to test continuous reads and accept the additional traffic. |

The first mode uses official integration events and the companion's own Bridge button event stream. Polling then helps track subsequent activity. Wheels and buttons have separate activity windows; mode and interval settings are shared.

The default interval is **0.1 s** and the activity window **3 s**. Interval and window fields appear when Continuous is selected; changing modes preserves saved values. The window governs temporary activity; Continuous also reads outside it.

Requests are batched per Bridge, not sent separately for each controller. Continuous reads at 0.1 s mean approximately **20 REST requests per second per Bridge**, plus an event stream. Shorter intervals increase network traffic and processing load on HA and Bridge. Requests do not overlap and failures cause backoff. These are experimental settings, not a manufacturer recommendation.

Motion uses official sensor state changes rather than this fast polling. Changing the mode therefore does not speed up motion detection.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing panel or new controls | Restart HA after installation, refresh the browser, use an administrator account. |
| Controller listed but inactive | Enable control, select targets and gesture, check the shared entity condition. |
| Unexpected colors or automatic changes | Concurrent Hue assignments, other automations and AL. |
| “Invalid flow specified” | Close the dialog, refresh the page and open fresh settings. If it recurs, inspect HA logs. |

When reporting a problem, include HA/integration versions, controller model, action, target entity type and reproduction steps. Do not publish your Bridge application key or access tokens.
