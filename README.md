# Hue Fluid Dimmer

*Smooth dimming. Low latency.*

An experimental Home Assistant companion for Philips Hue **Tap Dial**, **Smart Button** and **Dimmer v2** controllers and **Hue Motion sensors**. Configure targets and button gestures directly in the integration, without per-controller automations, duplicate controller entities or brightness helpers.

Requires **Home Assistant 2026.10.1 or newer**, a Hue v2 bridge and the configured official **Philips Hue** integration. This project is independent of Signify and Home Assistant.

## Installation and updates

1. Add `https://github.com/tommyzacek/hue-fluid-dimmer` to HACS custom repositories as an **Integration**.
2. Download the release and restart Home Assistant.
3. Add **Hue Fluid Dimmer** in **Settings → Devices & services**, then select your existing Hue bridge.
4. Open **Hue Fluid Dimmer** in the sidebar (administrators only). Expand your bridge and a **Dial / Button / Dimmer / Motion** group, then click a controller to open its configuration. Select targets and enable control. New controller rows start disabled.
5. The gear beside the bridge opens shared control conditions, Adaptive Lighting cooperation and polling settings directly in the panel. The original integration page and its configuration gears remain available. Refresh the browser after updating to load the new panel and form controls.

Alternatively copy `custom_components/hue_fluid_dimmer` into your HA configuration's `custom_components` directory and restart.

Disable competing direct Hue assignments, blueprints or automations for any gestures enabled here. Otherwise both systems may send commands. No official Hue integration settings, automations, scripts or scenes are modified by this integration.

## Controller overview and forms

The grouped sidebar panel is installed automatically with the integration; no separate dashboard or frontend download is needed. It lists real configured controllers and their enable flags, and opens Home Assistant's native configuration dialogs. It creates no extra bridges, devices or entities. The overview endpoint is restricted to administrators and exports only controller names, identifiers, types and enable flags. It adds no periodic polling.

Button, Dimmer and Tap Dial forms share Motion's switches, outlined selections and sliders. Custom Dial settings retain separate Lights and Other entities sections. Existing controller bindings, values and runtime behavior are preserved. The overview composes Home Assistant frontend components and therefore depends on their compatibility with the supported HA version.

## Supported controllers

| Controller | Models | Configuration |
| --- | --- | --- |
| Tap Dial | Discovered rotary resources | Dial and four buttons |
| Smart Button | ROM001, RDM003, RDM005 | One button |
| Dimmer v2 | RWL022 | ON/OFF, +, − and HUE buttons |
| Hue Motion | Discovered Hue motion services | Time periods, light targets, sensitivity and cycle policies |

New supported Smart Buttons and Dimmer v2 devices are added as disabled configuration rows when the integration loads. Deleted rows are not recreated on every reload; **Add controller** can restore them. Dimmer v1 and Hue wall modules are outside this release's scope.

Tap Dial control and a number-based PWM fan have been physically exercised at the development installation. New Smart Button/Dimmer integration-owned actions still require physical validation. RDM005 support is based on its model mapping, not a physical test.

## Dial

Button 1's short-press targets are the default main dial targets. An optional independent main target selection can control a larger room or a different light/device group. A long-press **Dial** action on buttons 2–4 temporarily borrows that button's short-press targets. Routing returns to the main targets after **5 seconds without a first rotation**, or **5 seconds after the last rotation**.

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

## Motion sensors

Motion reuses the official Hue integration's motion, illuminance and enable-switch states; it does not add fast sensor polling. Disable the sensor's competing native Hue lighting assignment before enabling its Hue Fluid Dimmer configuration. The official Hue integration and its sensor entities must remain available. The form warns when the official motion or illuminance sensor switch is off.

One time period is **All day**, with no editable start time. Add periods to partition the entire day: each period ends when the next one starts, including overnight. Each period has its own startup brightness/color, absence timer, optional target override and **Do not disturb** switch. Do not disturb prevents new cycles; an existing cycle can finish using the settings it started with. Sensitivities, ending style and manual-control policies are global to that Motion configuration.

- Brightness and color are independent. **Previous state** recovers per-light brightness from before Motion's own final dimming. That recovery is persisted and avoids repeated 100 → 50 → 25% reductions across cycles. A newer external off-to-on activation invalidates the saved recovery value. Configured percentage explicitly sends brightness; unchanged color sends no color setting.
- Timers start after motion becomes inactive, rather than expiring while the sensor continuously reports motion. New motion restores an ending in progress and postpones shutdown without repeatedly applying startup parameters. Timers range from 1 to 60 minutes, in half-minute steps up to 10 minutes and minute steps above.
- Startup and renewed-motion restoration use 0.5-second transitions; the final off command uses 2 seconds. The optional final 30 seconds can ramp to half the actual brightness, fade to off, or quickly dim to half over 2 seconds and hold until shutdown. The baseline is captured when the ending begins, including brightness changes made earlier in the cycle.
- Arrival, departure for already-on lights, manual changes, manual off, handover scope and return rules can be configured separately. Manual-action provenance is recognized only for controls executed by this integration; it is not inferred from arbitrary HA or Hue app state changes. Exposed HA light groups and Hue rooms/zones are resolved to their member lights where available.
- The live illuminance slider ranges to 650 lx, then **∞** for unrestricted operation. Finite thresholds use a strict below-threshold comparison. Disabled/unavailable illuminance cannot permit finite-threshold activation. Lux thresholds are evaluated locally; no native Hue lux rule is rewritten. Movement sensitivity has three positions and is written to Bridge only when saving an enabled Motion configuration.

Native Hue transitions can report their target brightness or off state immediately in HA while the physical light is still fading. History therefore does not measure the physical ramp. Smoothness, stop timing and return behavior still require testing with the selected devices.

## Shared state condition

Enable **Block control by entity**, select which controller families are subject to the condition (**Motion**, **Button**, **Dial**, **Dimmer**), choose a control entity, then type exact **Allowed states** separated by commas. No states are prefilled. The condition applies to all selected controller types on this bridge, across all time periods. Dial includes its buttons as well as rotation.

Other, unknown, unavailable or missing states block new actions from the selected families. Active held regulation is stopped; existing Motion cycles can expire and switch off, but blocked motion cannot extend them or restore brightness. Returning to an allowed state permits future input and does not itself switch lights on. Official sensor/event reporting is unaffected. The feature is optional and disabled by default; older Motion-only condition settings retain Motion-only scope. This is an action gate, not a security/alarm system.

## Adaptive Lighting cooperation

The optional bridge-level cooperation switch discovers Adaptive Lighting profiles through HA's registry/config entries and uses the public `adaptive_lighting.set_manual_control` service. Direct manual brightness/color changes mark only the corresponding supported components where the installed AL version allows it. Older versions may also pause color changes. Motion's temporary ending pauses preserve existing manual flags and are released separately. Explicit Motion startup brightness/color choices are treated as manual parameters; recovery of pre-ending brightness does not itself request a manual flag.

Groups are resolved to members and matched against each relevant AL profile. Only matching controlled lights are marked; unrelated lights are not included. If AL tracks an unexpanded group as one entity, a partial-member operation is skipped with a warning instead of marking the entire room. Control the whole AL group or enable AL's `expand_light_groups` option for member-level cooperation. Multiple matching profiles are handled separately. AL retains responsibility for resetting manual flags. Hue Fluid Dimmer does not silently change AL configuration or create profiles, and works without AL installed.

Ordinary light power toggles now issue explicit `light.turn_off` when any selected target is on, otherwise `light.turn_on`. This avoids the toggle-interception behavior observed with AL at the development installation. It does not guarantee that other automations or integrations cannot subsequently change the lights.

## Polling and connection

The default **After first event** mode uses official HA Hue events and the companion's timestamped button SSE stream to wake temporary batch reads. Rotary and button activity windows are separate; mode and interval are shared. **Continuous** reads both resource types while idle as well.

The form exposes interval/window fields only for **Continuous**; switching modes retains saved values. Shorter intervals and continuous idle reads increase network traffic and processing on HA and Bridge. **After first event** is the more economical default.

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

Doplněk k oficiální Hue integraci pro Tap Dial, Smart Button, Dimmer v2 a pohybové senzory Hue Motion. Ovladače mají vlastní nastavení přímo v integraci, bez nových zařízení, entit nebo pomocníků. Každý stisk lze samostatně zapnout a nastavit. Button a Dimmer používají výchozí zařízení, vlastní výběr se objeví až po zapnutí příslušného přepínače. Scény nejsou součástí nabídky; vlastní logiku lze zapojit skriptem.

Kolečko má oddělené nastavení pro světla a ostatní entity. Předvolby mají adaptivní přechod zapnutý. Dočasné přesměrování kolečka se vrací po 5 sekundách. Před zapnutím akce odstraň konkurenční přiřazení v Hue nebo automatizacích. Po aktualizaci restartuj HA a obnov stránku pro načtení nových překladů.

Motion má navazující časové bloky s vlastním jasem, barvou a časovačem, tři styly závěrečného zhasnutí a samostatné chování při ručním ovládání. Jas před závěrečným ztlumením se ukládá, aby se při dalších cyklech opakovaně nepůlil. V hlavním nastavení lze jednotlivé typy ovladačů podmínit stavem libovolné entity; povolené stavy se píší ručně. Spolupráce s Adaptive Lighting je volitelná. U AL skupin bez rozbalení členů nelze bezpečně předat ruční příznak jen části skupiny; ovládej celou skupinu nebo použij `expand_light_groups`.
