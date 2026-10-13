# Hue Fluid Dimmer

*Smooth dimming. Low latency.*

An **experimental Home Assistant companion integration** for Hue Tap Dial controllers. It uses the configured official Hue integration and reads the bridge's latest rotary reports to reduce the delay of continuous rotary gestures.

Configure every controller's lights and optional button actions in the integration's options. No per-controller automation or brightness helper is required. This project does not replace or modify the built-in `hue` integration. It is not an official Signify or Home Assistant product.

**Status:** initial development release. Automated tests run against Home Assistant 2026.10.1. The complete integration has not yet been validated with physical lights; responsive polling alone does not prove smooth dimming.

## Installation

Requires Home Assistant **2026.10.1 or newer** and a working official **Philips Hue v2** integration.

1. In HACS, open **Custom repositories**, add `https://github.com/tommyzacek/hue-fluid-dimmer`, and choose **Integration**.
2. Download Hue Fluid Dimmer and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Hue Fluid Dimmer**.
4. Select an already configured Hue bridge.
5. Each discovered Tap Dial appears as a **controller configuration row** under the bridge. Click its **Configure gear** to open that controller’s light and button settings directly. Select its lights and enable its control.
6. The bridge’s own **Configure** button opens polling settings. New controllers can be added with **Add controller** after reloading the integration.

Alternatively copy `custom_components/hue_fluid_dimmer` into your HA configuration's `custom_components` directory and restart.

**Before enabling a controller**, disable any blueprint or other automation that already dims the same lights from its dial, and remove any direct Hue dial assignment for those lights. Otherwise multiple controllers of the same gesture will conflict. Buttons without an assignment in this integration keep working with existing HA automations.

## Polling modes

| Mode | Behavior | Limitation |
| --- | --- | --- |
| Only during activity (default) | Rotary or button events wake temporary reads for that resource type across the entire bridge. | The first wake-up still waits for an event. |
| Continuous | Both resource types are read while the integration is loaded. | More bridge traffic even while idle; button actions still use SSE history. |

The default interval is **100 ms**, configurable up to 2 seconds; the active window defaults to 3 seconds. Dials use one batch request to `/clip/v2/resource/relative_rotary`; buttons use one batch request to `/clip/v2/resource/button`, regardless of controller count. Mode and interval are shared; each resource type has its own activity window. Continuous mode at 100 ms therefore sends approximately 20 REST requests per second per bridge, plus its SSE stream. Active button reads continue until recognition is complete and then stop after the activity window. Requests never overlap. HTTP/network errors trigger exponential backoff, up to 30 seconds. After an outage, the first successful read establishes a baseline instead of replaying old movement.

100 ms is an experimental tuning choice, **not a verified vendor recommendation or a claim of negligible bridge load**. A bridge returns only its latest report, not a queue of every physical detent. Faster movement can overwrite intermediate reports between reads. Native Zigbee/Hue control may therefore remain smoother. Continuous polling cannot recover information the bridge never exposes.

## Controller settings

The controller dialog has one **Dial** section and four collapsible **Button** sections. Control is off by default.

| Dial profile | Sensitivity (percentage points / 15 steps) | Transition |
| --- | --- | --- |
| Gentle | 0.75 | 1 second |
| Balanced | 1.5 | 1 second |
| Swift | 3 | 0.5 seconds |
| Custom | User choice | User choice |

Only **Custom** exposes the sensitivity and transition fields. Custom values are remembered when changing profiles. Presets are initial experimental tuning choices; they do not change event arrival latency or the bridge polling interval. Existing settings and light selections are preserved when upgrading.

For **Controlled lights**, choose **Same as button 1–4** or **Custom lights**. The custom entity picker appears only for Custom lights. Shared selections resolve the button's current **short-press** targets on each rotary report, including an individual light, a HA light group or a list of lights. Changing that button's light targets updates the dial's selection automatically.

Quick selections support only lights/groups/lists of lights. For a button that activates a scene or script, choose **Custom lights** for the dial. No script parsing or guessing of scene targets is performed.

Each button has independent **Short press**, **Long press**, **Double press** and **Triple press** checkboxes. Enabling one reveals its target picker: one or more light/group entities, or one scene or script. Lights toggle; scenes/scripts activate. Mixed light/scene/script selections are rejected. Disabling a gesture removes its stored targets, and saving reloads the integration and cancels pending recognition/actions. Existing short-release assignments migrate automatically.

Short press executes on release with **no recognition delay** when double/triple press is disabled for that button. Long press executes once on `long_press`; repeats and release do not execute it again. Double press executes on the second release unless triple press is enabled; triple press executes on the third release. A sequence never also executes its constituent short actions. If a recognized gesture has no assignment, it does nothing rather than falling back to another action.

Multi-press recognition compares the next press with the preceding release using **Bridge timestamps**, with a **400 ms interval**. A later press starts a new sequence. Tap Dial SSE may deliver events in approximately one-second batches; this latency cannot be removed just by shortening a timer.

REST polling confirms quiet time while SSE remains the authoritative ordered press history. A repeated REST report at least 400 ms after its first observed receipt can finish a matching pending SSE sequence immediately, rather than add a fixed 1.4-second delivery grace. Confirmation requires a fresh query and the exact same release timestamp. A newer REST report holds expiry until its missing SSE transitions arrive. Polling snapshots never count as an extra press or guess missing initial/release pairs. The entire SSE frame is processed before quiet confirmation; out-of-order snapshots are ignored. This prevents polling gaps from turning a double press into a short press in the tested sequences.

When REST is unavailable, recognition retains its conservative **1.4-second grace after receipt**. This is a fallback, not a guaranteed network-delay bound. In continuous mode REST observes state earlier, but this conservative version still requires SSE history before executing button actions. Short-only bindings remain immediate on SSE release. The new timing requires physical validation after installation.

A single additional read-only **SSE connection per configured bridge** handles all Tap Dial buttons. Its timestamped reports are the sole source of button actions; public `hue_event` button reports do not execute a second copy. Disconnect/unload cancels pending gestures, and reconnect requires a new initial press instead of executing an orphan release. Disable other automations or direct Hue assignments for the gestures you enable here to avoid independent actions.

The dimmer holds its target in memory during a gesture, so delayed light state reports do not move its reference value. After 3 idle seconds it resynchronizes from available selected lights. Identical light selections share a target. Partially overlapping selections remain independent; avoid operating them simultaneously. Grouping lights in HA may generate several underlying Hue commands. Commands are serial and coalesced per selection, at most four service calls per second; that is **not** a bridge-wide limit on underlying light commands.

Transitions depend on the selected light integration. The first release needs physical testing of turn-on, direction reversals, button-to-dial changes and multiple controllers. Scenes/scripts can change lights asynchronously; immediate dial movement after such an action can still observe delayed HA state.

## Advanced use

The companion creates **no controller entities or brightness helpers**. Each initially discovered dial gets a native **configuration subentry** in the integration’s controller list. Its gear opens the settings modal directly; the row has no link to an empty device/entity page. It emits the bus event `hue_fluid_dimmer_event` for advanced automations, with:

```yaml
resource_id: "rotary-resource-id"
owner_id: "hue-device-id"
updated: "2026-01-01T00:00:01+00:00"
action: "repeat"
direction: "clock_wise"
steps: 15
duration: 100
```

The timestamp comes from the bridge; it is not a measurement of the physical rotation time. The same or older report timestamp is ignored. Official rotary events only wake polling and are never applied as additional dimming steps. Historic reports at startup are ignored. For newly paired controllers, reload the integration and choose **Add controller**. Their old report is baselined when discovered. Removing a configuration row disables its control and does not recreate it on reload; **Add controller** can restore it.

The companion creates **no device or entity registry records**. Official Hue devices and entities remain untouched. Upgrading from 0.1.1/0.1.2 converts existing controller bindings to configuration subentries, retaining their enabled state, lights, sensitivity, transitions and button assignments. Companion device names set by the user become the row titles. Its former device records and `event.*_fast_rotation` entities are removed; any automation referencing those old companion records must be adjusted. Bus events remain available.

## How it connects to Hue

The public HA event bus and button SSE events wake polling. Rotary resources use HA's shared HTTP session; one additional SSE subscription per bridge supplies timestamped button reports. No extra pairing flow is needed. The adapter obtains the selected Hue config entry's current `host` and `api_key` in memory and uses HA's shared HTTP session. It does not copy the application key into its own config entry, diagnostics, repository, or logs.

Reading the public event bus is a documented HA integration mechanism. The Hue credential field names are an implementation dependency, not a separately versioned public credential-sharing API. That dependency is isolated in `Runtime.credentials` and may need updating after a Hue integration change. The bridge must remain configured and loaded in the official integration. Local bridge HTTPS certificate verification follows the current official Hue integration's approach and is disabled for these requests.

Options changes reload the companion and establish fresh report baselines. Unloading cancels polling, the button stream, button polling, pending gesture timers/actions, light workers and the native event subscription. No automations, helpers, Hue files or official integration options are edited.

Diagnostics expose only counters and polling settings; controller bindings are redacted.

## Development and public distribution

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
```

Physical Tap Dial button sequences were captured directly from the Bridge and replayed in automated tests. The new button UI and actions still need installation and physical validation. Button and Dimmer models remain unsupported in this release pending model-specific validation.

Tests use synthetic reports and cover duplicate/out-of-order suppression, startup baselines, unavailable lights, in-memory brightness targets, direction reversals, command coalescing, polling wake/sleep, failed-request backoff, button routing and GUI schemas against real HA classes, including controller reconfiguration and registry-to-subentry migration. A synthetic 100-resource test checks batch behavior; it does not demonstrate support for 100 physical controllers on one Hue bridge.

This public repository can be added to HACS without inclusion in its default catalog. Default catalog submission and Home Assistant Core inclusion are separate review processes. CI includes Ruff, pytest, hassfest and HACS validation; brand validation is intentionally skipped because no catalog/brand submission has been made.

Relevant official documentation: [HA event listeners](https://developers.home-assistant.io/docs/integration_listen_events/), [integration dependencies](https://developers.home-assistant.io/docs/creating_integration_manifest/), [appropriate polling](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/appropriate-polling/), [HACS inclusion](https://www.hacs.xyz/docs/publish/include/).

## Česky

Experimentální doplněk k oficiální Hue integraci. Vybereš Bridge; ovladače se zobrazí jako konfigurační položky. Ozubené kolečko u ovladače otevře přímo jeho nastavení. Nevznikají další zařízení, entity, automatizace ani pomocníci. Každému tlačítku můžeš samostatně zapnout krátký, dlouhý, dvojitý a trojitý stisk a přiřadit jim scénu, skript nebo přepnutí světla. Krátký stisk bez vícekliků nemá přidané čekání. Vícekliky mají hranici 400 ms mezi uvolněním a dalším stiskem. REST potvrzuje klid a zkracuje čekání, stream zachovává úplnou sekvenci. Bez REST zůstává rezervní čekání 1,4 s po přijetí. Zpoždění doručování streamu zůstává. Vypnutí volby odstraní její vazbu.

Výchozí režim čte kolečka a tlačítka dočasně po první události; trvalý režim čte oba typy i v klidu. Režim a interval jsou společné. Trvalé čtení reaguje bez tohoto čekání, ale posílá požadavky i v klidu. Kolečka a tlačítka používají dva hromadné požadavky na Bridge. Bridge poskytuje poslední report, nikoli všechny jednotlivé kroky kolečka.

Před zapnutím ovládání vypni původní blueprint pro stejný ovladač. Celou integraci je ještě potřeba otestovat se skutečnými světly; první vydání proto není zárukou chování stejného jako v Hue aplikaci.

