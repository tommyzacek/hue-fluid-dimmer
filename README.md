# Hue Rotary Fast

An **experimental Home Assistant companion integration** for Hue Tap Dial controllers. It uses the configured official Hue integration and reads the bridge's latest rotary reports to reduce the delay of continuous rotary gestures.

Configure every controller's lights and optional button actions in the integration's options. No per-controller automation or brightness helper is required. This project does not replace or modify the built-in `hue` integration. It is not an official Signify or Home Assistant product.

**Status:** initial development release. Automated tests run against Home Assistant 2026.10.1. The complete integration has not yet been validated with physical lights; responsive polling alone does not prove smooth dimming.

## Installation

Requires Home Assistant **2026.10.1 or newer** and a working official **Philips Hue v2** integration.

1. In HACS, open **Custom repositories**, add `https://github.com/tommyzacek/hue-rotary-fast`, and choose **Integration**.
2. Download Hue Rotary Fast and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Hue Rotary Fast**.
4. Select an already configured Hue bridge.
5. Open **Configure → Controller**, select a controller, select its lights and enable its control. Repeat for other controllers.

Alternatively copy `custom_components/hue_rotary_fast` into your HA configuration's `custom_components` directory and restart.

**Before enabling a controller**, disable any blueprint or other automation that already dims the same lights from its dial, and remove any direct Hue dial assignment for those lights. Otherwise multiple controllers of the same gesture will conflict. Buttons without an assignment in this integration keep working with existing HA automations.

## Polling modes

| Mode | Behavior | Limitation |
| --- | --- | --- |
| Only during rotation (default) | A public `hue_event` wakes one polling loop for the entire bridge. Fresh movement extends the active window. | The first action still waits for the official Hue event. |
| Continuous | The same loop runs while the integration is loaded. | More bridge traffic even while idle. |

The default interval is **100 ms**, configurable up to 2 seconds; the active window defaults to 3 seconds. There is one batch request to `/clip/v2/resource/relative_rotary` per cycle per bridge, regardless of the number of configured controllers. Requests never overlap. HTTP/network errors trigger exponential backoff, up to 30 seconds. After an outage, the first successful read establishes a baseline instead of replaying old movement.

100 ms is an experimental tuning choice, **not a verified vendor recommendation or a claim of negligible bridge load**. A bridge returns only its latest report, not a queue of every physical detent. Faster movement can overwrite intermediate reports between reads. Native Zigbee/Hue control may therefore remain smoother. Continuous polling cannot recover information the bridge never exposes.

## Controller settings

- **Enable control:** off by default; event entities remain available without controlling lights.
- **Lights:** any HA lights supporting brightness and transitions. Multiple lights are treated as one selection.
- **Sensitivity:** percentage points per 15 reported steps, default 1.5. Larger reported rotations produce proportionally larger changes.
- **Transition:** seconds for each light's native brightness ramp, default 1 second. The integration sends absolute brightness with a transition rather than implementing a queue of small increments.
- **Buttons 1–4:** optional scene, script or light. A short release activates the scene/script or toggles the light. Long presses are left to existing HA automations.

The dimmer holds its target in memory during a gesture, so delayed light state reports do not move its reference value. After 3 idle seconds it resynchronizes from available selected lights. Identical light selections share a target. Partially overlapping selections remain independent; avoid operating them simultaneously. Grouping lights in HA may generate several underlying Hue commands. Commands are serial and coalesced per selection, at most four service calls per second; that is **not** a bridge-wide limit on underlying light commands.

Transitions depend on the selected light integration. The first release needs physical testing of turn-on, direction reversals, button-to-dial changes and multiple controllers. Scenes/scripts can change lights asynchronously; immediate dial movement after such an action can still observe delayed HA state.

## Advanced use

Each dial exposes an event entity with `start` and `repeat` events. The companion also emits `hue_rotary_fast_event` with:

```yaml
resource_id: "rotary-resource-id"
owner_id: "hue-device-id"
updated: "2026-01-01T00:00:01+00:00"
action: "repeat"
direction: "clock_wise"
steps: 15
duration: 100
```

The timestamp comes from the bridge; it is not a measurement of the physical rotation time. The same or older report timestamp is ignored. Official rotary events only wake polling and are never applied as additional dimming steps. Historic reports at startup are ignored. New controllers require an integration reload to add their event entities; their old report is baselined when discovered.

Event entities appear on companion controller devices, separate from the official Hue devices. This avoids changing the official integration's device registry ownership.

## How it connects to Hue

The public HA event bus is the wake-up mechanism. One additional persistent HTTP session reads rotary resources; there is no second SSE subscription and no extra pairing flow. The adapter obtains the selected Hue config entry's current `host` and `api_key` in memory and uses HA's shared HTTP session. It does not copy the application key into its own config entry, diagnostics, repository, or logs.

Reading the public event bus is a documented HA integration mechanism. The Hue credential field names are an implementation dependency, not a separately versioned public credential-sharing API. That dependency is isolated in `Runtime.credentials` and may need updating after a Hue integration change. The bridge must remain configured and loaded in the official integration. Local bridge HTTPS certificate verification follows the current official Hue integration's approach and is disabled for these requests.

Options changes reload the companion and establish fresh report baselines. Unloading cancels polling, light workers and the native event subscription. No automations, helpers, Hue files or official integration options are edited.

Diagnostics expose only counters and polling settings; controller bindings are redacted.

## Development and public distribution

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
```

Tests use synthetic reports and cover duplicate/out-of-order suppression, startup baselines, unavailable lights, in-memory brightness targets, direction reversals, command coalescing, polling wake/sleep, failed-request backoff, button routing and GUI schemas against real HA classes. A synthetic 100-resource test checks batch behavior; it does not demonstrate support for 100 physical controllers on one Hue bridge.

This public repository can be added to HACS without inclusion in its default catalog. Default catalog submission and Home Assistant Core inclusion are separate review processes. CI includes Ruff, pytest, hassfest and HACS validation; brand validation is intentionally skipped because no catalog/brand submission has been made.

Relevant official documentation: [HA event listeners](https://developers.home-assistant.io/docs/integration_listen_events/), [integration dependencies](https://developers.home-assistant.io/docs/creating_integration_manifest/), [appropriate polling](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/appropriate-polling/), [HACS inclusion](https://www.hacs.xyz/docs/publish/include/).

## Česky

Experimentální doplněk k oficiální Hue integraci. V nastavení vybereš Bridge, ovladač a světla; pro každý ovladač nemusíš vytvářet automatizaci ani pomocníka. Tlačítkům můžeš přiřadit scénu, skript nebo přepnutí světla.

Výchozí režim čte Bridge jen při otáčení a čeká na první událost z oficiální integrace. Trvalé čtení reaguje bez tohoto čekání, ale posílá požadavky i v klidu. Jeden požadavek čte všechny ovladače na daném Bridge. Bridge poskytuje poslední report, nikoli všechny jednotlivé kroky kolečka.

Před zapnutím ovládání vypni původní blueprint pro stejný ovladač. Celou integraci je ještě potřeba otestovat se skutečnými světly; první vydání proto není zárukou chování stejného jako v Hue aplikaci.

