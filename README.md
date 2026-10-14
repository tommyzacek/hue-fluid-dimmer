# Hue Fluid Dimmer

*Smooth dimming. Low latency.*

An experimental Home Assistant companion integration for Hue Tap Dial controllers. It uses an existing official Hue integration, reads rotary reports from the Bridge and configures button actions without per-controller automations or brightness helpers. It is not an official Signify or Home Assistant product.

## Installation

Requires Home Assistant **2026.10.1 or newer** and a configured official **Philips Hue v2** integration.

1. Add `https://github.com/tommyzacek/hue-fluid-dimmer` as an **Integration** in HACS Custom repositories.
2. Download and restart Home Assistant.
3. Add **Hue Fluid Dimmer** in Settings → Devices & services and select your existing Hue bridge.
4. Open a discovered controller's Configure gear, assign button 1's short-press targets and enable control.

Alternatively copy `custom_components/hue_fluid_dimmer` into your HA configuration and restart.

Disable competing blueprints, automations and direct Hue assignments for gestures controlled by this integration. Unassigned gestures can continue to be handled elsewhere. Configuration rows do not create duplicate device or event entities.

## Dial and temporary targets

The main dial controls button 1's short-press targets: lights, light groups, lists of lights, fans or number entities. Scenes and scripts cannot be dial targets.

For buttons 2–4, enable a short action with percentage targets and choose **Dial** for the long action. Holding that button temporarily borrows its short-press targets without toggling them. Routing returns to button 1 after **5 seconds without a first rotation**, or **5 seconds after the last rotation**. Routing is local to each controller and resets on reload.

| Profile | Light sensitivity / 15 reported steps | Light transition | Fan/number sensitivity / 15 steps | Fan/number ramp |
| --- | --- | --- | --- | --- |
| Gentle | 0.75 percentage points | 1 s | 0.75 percentage points | 1 s |
| Balanced | 1.5 percentage points | 1 s | 1.5 percentage points | 0.75 s |
| Swift | 3 percentage points | 0.5 s | 3 percentage points | 0.5 s |
| Custom | Independent setting | Independent setting | Independent setting | Independent setting |

Custom settings are grouped under **Lights** and **Other entities**, and are preserved when switching presets. Optional **adaptive transitions** apply only to Custom: report cadence determines a short transition, bounded by the configured duration and 0.5 seconds. Changes in direction discard the previous goal and follow the current estimated level. It remains experimental and does not remove Bridge event latency. The option is off by default.

Number entities are normalized using their min/max range and rounded to their supported step. Fan/number ramp values are sent through HA services approximately every 100 ms; lights execute their supported transition. Device reporting and physical behavior can differ.

## Buttons

Each of the four buttons has independently enabled short, long, double and triple actions. Turning an action off removes its binding.

- **Off / on**: normal light/fan toggle; number entities switch between minimum and maximum.
- **Off / previous percentage**: restore a recorded previous nonzero level, saved across reloads.
- **Off / configured percentage**: toggle to a chosen percentage.
- **Continuous regulation while held**: long press only. Start upward, skip one repeat at maximum and reverse downward. Release stops additional commands.
- **Dial**: long press on buttons 2–4 only, as described above.

Normal actions can also recall a scene or run a script. Native Hue held dimming reads actual Bridge brightness, uses relative dimming commands and stops on release. Other targets use HA services.

Short-only bindings have no multiclick waiting window. With double/triple actions enabled, recognition uses a **350 ms** interval between release and the next press, using Bridge timestamps. REST reads complement the button event stream; missing intermediate transitions wait for stream history rather than inventing clicks.

## Bridge polling

The default mode reads during activity; Continuous mode also reads while idle. The default polling interval is **100 ms**. Dials and buttons each use one batch request per Bridge, regardless of controller count, plus a button SSE stream. Continuous mode at 100 ms therefore sends approximately 20 REST requests per second per Bridge. Network errors cause backoff and fresh baselines after recovery.

The Bridge exposes its latest report, not every physical detent. Polling cannot recover overwritten reports. These settings are experimental, not a verified vendor traffic recommendation or a guarantee of native Hue latency.

The companion uses the official integration's credentials in memory and HA's shared HTTP session. It does not save credentials in its own configuration or diagnostics. Compatibility depends on the official integration's credential fields. No official Hue files or automation YAML files are modified.

## Updates and validation

See [v0.5.0 release notes](RELEASE_NOTES.md). After a HACS update, restart HA and refresh the browser for new form labels.

Physical tests covered Tap Dial control, Hue held dimming and a numeric PWM fan. Hue Button and Dimmer controller models remain unsupported pending model-specific validation. An intermittent external change to roughly 8% brightness is being investigated; this release does not claim a fix.

Automated tests cover report tracking, gesture recognition, temporary routing, configuration migration, percentage controls, restoration and adaptive transitions. A synthetic 100-resource test verifies batching, not 100 physical devices on one Bridge.

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
```

The repository can be installed as a HACS custom repository without default catalog inclusion. HACS catalog and HA Core inclusion are separate review processes.

## Česky

Hlavní cíl kolečka určuje krátký stisk tlačítka 1. Tlačítka 2–4 mohou dlouhým stiskem dočasně převzít kolečko pro své cíle; návrat nastane po 5 sekundách nečinnosti. Vlastní nastavení odděluje citlivost a přechod světel od citlivosti a rampy ostatních entit. Adaptivní přechod je volitelný a experimentální. Tlačítka podporují přepnutí, předchozí nebo nastavené procento a plynulou regulaci při držení. Bez pomocníků a samostatných automatizací pro každý ovladač.
