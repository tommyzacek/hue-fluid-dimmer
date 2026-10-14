# Hue Fluid Dimmer

*Smooth dimming. Low latency.*

An experimental Home Assistant companion for Philips Hue **Tap Dial**, **Smart Button** and **Dimmer v2** controllers. Configure targets and button gestures directly in the integration, without per-controller automations, duplicate controller entities or brightness helpers.

Requires **Home Assistant 2026.10.1 or newer**, a Hue v2 bridge and the configured official **Philips Hue** integration. This project is independent of Signify and Home Assistant.

## Installation and updates

1. Add `https://github.com/tommyzacek/hue-fluid-dimmer` to HACS custom repositories as an **Integration**.
2. Download the release and restart Home Assistant.
3. Add **Hue Fluid Dimmer** in **Settings → Devices & services**, then select your existing Hue bridge.
4. Open a controller's **Configure** gear, select targets and enable control. New controller rows start disabled.
5. The bridge's **Configure** button opens polling settings. Refresh the browser after updating to load new form translations.

Alternatively copy `custom_components/hue_fluid_dimmer` into your HA configuration's `custom_components` directory and restart.

Disable competing direct Hue assignments, blueprints or automations for any gestures enabled here. Otherwise both systems may send commands. No official Hue integration settings, automations, scripts or scenes are modified by this integration.

## Supported controllers

| Controller | Models | Configuration |
| --- | --- | --- |
| Tap Dial | Discovered rotary resources | Dial and four buttons |
| Smart Button | ROM001, RDM003, RDM005 | One button |
| Dimmer v2 | RWL022 | ON/OFF, +, − and HUE buttons |

New supported Smart Buttons and Dimmer v2 devices are added as disabled configuration rows when the integration loads. Deleted rows are not recreated on every reload; **Add controller** can restore them. Dimmer v1 and Hue wall modules are outside this release's scope.

Tap Dial control and a number-based PWM fan have been physically exercised at the development installation. New Smart Button/Dimmer integration-owned actions still require physical validation. RDM005 support is based on its model mapping, not a physical test.

## Dial

Button 1's short-press targets are the main dial targets. A long-press **Dial** action on buttons 2–4 temporarily borrows that button's short-press targets. Routing returns to the main targets after **5 seconds without a first rotation**, or **5 seconds after the last rotation**.

| Profile | Light sensitivity¹ | Light transition | Other entity sensitivity¹ | Other entity ramp |
| --- | --- | --- | --- | --- |
| Gentle | 1.2 | 1 s | 0.75 | 1 s |
| Balanced | 2.4 | 1 s | 1.5 | 0.75 s |
| Swift | 4.8 | 0.5 s | 3 | 0.5 s |
| Custom | User choice | User choice | User choice | User choice |

¹ Base percentage points per 15 reported steps. Adaptive behavior changes the response according to rotation cadence; these are not guaranteed physical brightness increments.

All named profiles enable adaptive transitions. Custom exposes separate **Lights** and **Other entities** groups, with their own sensitivity and transition/ramp fields, plus an adaptive toggle. Custom values are retained when switching profiles. Profile changes affect the command response, not event arrival latency.

Lights use their integration's transition support; fan and number entities use a software ramp with HA services, respecting the entity's range/step. Actual smoothness depends on device capabilities, reporting and network delays. Future targets are discarded when rotation changes direction.

## Buttons

Short, long, double and triple presses have independent enable switches and actions. Short press is immediate on release when no multiclick action is enabled. Multiclick recognition uses Bridge timestamps with a **350 ms** interval; transport delays can add latency.

Actions include off/on, off/previous percentage and off/configured percentage. Targets can be lights/groups, fans, number entities or one script. Scene selection and scene cycling are not provided. Percentage regulation requires compatible percentage targets; unrelated target types cannot be mixed in a single ramp.

Smart Button and Dimmer have **Default lights / devices**. An action uses these unless **Use different devices for this action** is enabled; only then does its own target picker appear. Turning this override off returns to the defaults and discards the old target override. Disabling a gesture removes its binding.

Long press additionally supports **continuous regulation while held**. Direction is chosen once at the start: below 30% upward, above 60% downward, otherwise opposite the previous hold (first hold upward). It stops at the endpoint and on release, without reversing during the same hold. Dimmer +/− use fixed directions; short presses step by 10 percentage points. Native Hue held regulation uses relative dimming and a stop command; other targets use HA services. Device/network delays may still affect the visible stop.

## Polling and connection

The default **After first event** mode uses official HA Hue events and the companion's timestamped button SSE stream to wake temporary batch reads. Rotary and button activity windows are separate; mode and interval are shared. **Continuous** reads both resource types while idle as well.

Default interval: **100 ms**; default activity window: **3 s**. Each resource type uses one batch request for the whole bridge (`relative_rotary` and `button`), independent of controller count. Continuous mode at 100 ms is approximately 20 REST requests/s per bridge plus one SSE stream. Requests do not overlap; failures apply backoff. This experimental polling interval is not a verified vendor recommendation.

REST snapshots and timestamped SSE reports share a gesture state machine. Missing transitions wait for SSE history; duplicate/old reports are ignored. Startup/reconnection establishes fresh baselines instead of replaying old actions. A bridge exposes its latest rotary report, not every physical detent, so polling cannot recover overwritten movement.

The official Hue integration must remain configured and loaded. The companion reads its host and application key in memory and uses HA's shared HTTP session; no extra pairing is needed and the key is not copied into companion configuration or diagnostics. The official integration's credential field names are an implementation dependency. Bridge HTTPS certificate verification follows the existing local Hue approach and is disabled for these requests.

Unloading/reconfiguring cancels polling, stream subscriptions, gesture timers, routing and active ramps. Diagnostics redact controller bindings. The `hue_fluid_dimmer_event` bus event remains available for advanced rotary automations.

## Languages

The HA profile language selects **Czech**, **Slovak** or **English**. English is the fallback for other languages. Controller names and user-created entity names retain their own names.

## Development

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
```

CI runs tests, Ruff, hassfest and HACS validation. HACS custom repository installation does not require inclusion in its default catalog; catalog submission and Home Assistant Core inclusion are separate processes.

Tests cover report baselines/deduplication, batch polling, multiclick recognition, model discovery, native HA form schemas, target overrides, routing, percentage controls and held regulation. Synthetic controller-count tests are not physical scalability validation. A previously observed external brightness drop to approximately 8% remains without a confirmed cause; this release does not claim a fix.

## Česky

Doplněk k oficiální Hue integraci pro Tap Dial, Smart Button a Dimmer v2. Ovladače mají vlastní nastavení přímo v integraci, bez nových zařízení, entit nebo pomocníků. Každý stisk lze samostatně zapnout a nastavit. Button a Dimmer používají výchozí zařízení, vlastní výběr se objeví až po zapnutí příslušného přepínače. Scény nejsou součástí nabídky; vlastní logiku lze zapojit skriptem.

Kolečko má oddělené nastavení pro světla a ostatní entity. Předvolby mají adaptivní přechod zapnutý. Dočasné přesměrování kolečka se vrací po 5 sekundách. Před zapnutím akce odstraň konkurenční přiřazení v Hue nebo automatizacích. Po aktualizaci restartuj HA a obnov stránku pro načtení nových překladů.

## Known interaction: Adaptive Lighting and button toggles

At the development installation, three Smart Button short presses each produced one `light.toggle` request for the bathroom light list. Adaptive Lighting immediately produced a child `light.turn_on` call for the available members, and the lights remained on. One selected member was unavailable. This is an observed interaction, not a confirmed root cause for every toggle failure or an upstream fix.

Adaptive Lighting's `intercept` and `multi_light_intercept` options were both enabled. A diagnostic workaround is to test disabling `multi_light_intercept` for the affected Adaptive Lighting entry first, then `intercept` if necessary. This has not yet been tested at this installation. Disabling interception can change how promptly adaptive brightness/color is applied when lights turn on. Automatic adaptation need not be disabled entirely.

An integration-side alternative under consideration is explicit `light.turn_off` when any target is on, otherwise `light.turn_on`. It has not been implemented in v0.7.0. No Adaptive Lighting settings are changed automatically by Hue Fluid Dimmer.
