# Technical notes and development

[Čeština](../README.cs.md) | [Slovenština](../README.sk.md) | [English](../README.md)

These implementation notes complement the user guides. Documentation follows the current development state; published release notes identify the features in each release.

## Local checks

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
```

CI runs tests, Ruff, hassfest and HACS validation. HACS custom repository installation does not require inclusion in its default catalog. Catalog submission and Home Assistant Core inclusion are separate processes. Synthetic controller-count tests are not physical scalability validation.

## Connection and event handling

The official Hue integration must remain configured and loaded. Hue Reconfigo reads its host/application key in memory and uses HA's shared HTTP session. No extra pairing is needed; the key is not copied into companion configuration or diagnostics. The official integration's credential field names are an implementation dependency. Bridge HTTPS certificate verification follows the existing local Hue approach and is disabled for these requests.

REST snapshots and timestamped button SSE reports share a gesture state machine. Missing transitions wait for SSE history; duplicate/old reports are ignored. Startup/reconnection establishes fresh baselines instead of replaying old actions. Bridge exposes its latest rotary report, not every physical detent; polling cannot recover overwritten movement.

The default polling interval is 100 ms and activity window 3 s. Each resource type uses one batch request per Bridge (`relative_rotary`, `button`), independent of controller count. Continuous mode at 100 ms is approximately 20 REST requests/s per Bridge plus an SSE stream. Requests do not overlap; failures apply backoff. These experimental intervals are not verified vendor recommendations.

Unloading cancels polling, subscriptions, gesture timers, routing and ramps. Controller configuration updates are handled separately; Motion configuration changes explicitly reset that Motion's running cycle. Diagnostics redact controller bindings. The `hue_reconfigo_event` bus event remains available for advanced rotary automations.

## Frontend and models

The grouped sidebar overview is restricted to administrators. Its endpoint exposes controller names, identifiers, types and enable flags, not credentials. The overview adds no periodic polling. It composes HA frontend components, so compatibility depends on the supported HA version.

New supported Smart Buttons and Dimmer v2 devices are added as disabled configuration rows when the integration loads. Deleted rows are not recreated on every reload; Add controller can restore them. RDM005 support is based on model mapping rather than a physical test of every function. Dimmer v1 and wall modules are outside the current support scope.

## Adaptive Lighting: observed toggle interaction

During development, three Smart Button short presses each produced one `light.toggle` request for a bathroom light selection. Adaptive Lighting immediately produced child `light.turn_on` calls for available members, and lights remained on. One selected member was unavailable. AL's `intercept` and `multi_light_intercept` were enabled. This is an observed interaction, not a universal explanation for toggle failures or an upstream fix.

The current implementation resolves ordinary light power toggles into explicit `light.turn_off` when any selected target is on, otherwise `light.turn_on`. This avoids the observed toggle interception path. It does not prevent other integrations/automations from subsequently controlling lights. The v0.7.0 README described explicit power commands as a future alternative; that statement was historical, not current behavior.

Bridge-level AL cooperation uses the public `adaptive_lighting.set_manual_control` service. Known group members are matched to relevant AL configurations. Partial control of an unexpanded AL group is skipped with a warning rather than marking unrelated members. Newer AL versions permit separate brightness/color components; older versions may pause both. Configuration is not silently changed and profiles are not created. See the Bridge guides for user-facing behavior.

## Physical brightness and state reporting

Hue may report the target brightness or off state immediately while a physical transition is still in progress. HA history is therefore not a physical ramp measurement. The integration does not fabricate intermediate states on official entities. Test smoothness and stopping with the actual target devices.

A previously observed external brightness drop to approximately 8% remains without a confirmed cause. Documentation does not claim a fix for it.
