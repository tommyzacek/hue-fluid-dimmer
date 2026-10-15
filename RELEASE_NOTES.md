# v0.9.5 — Grouped controller overview and consistent forms

**Pre-release / experimental.** Requires Home Assistant 2026.10.1+, a Hue v2 Bridge and the official Hue integration.

- Add an automatically installed, administrator-only **Hue Fluid Dimmer** sidebar panel. Expand the bridge and **Dial / Button / Dimmer / Motion** groups to configure each controller.
- Open the existing native Home Assistant controller dialogs directly from the overview. No duplicate bridges, devices or entities are created.
- Add a gear beside each bridge that opens its shared settings in place, without leaving the panel. Preserve the original integration page and its Bridge settings gear.
- Unify Button, Dimmer and Tap Dial forms with Motion: switches, outlined selections, profile dropdowns, percentage and numeric sliders. Retain separate **Lights / Other entities** headings for Custom Dial settings.
- Preserve existing bindings, configuration values and controller behavior. The overview adds no periodic polling, and its admin-only endpoint exports only names, identifiers, types and enable flags.

Validation: **277 tests passed**, Ruff lint/format and JavaScript syntax checks. The grouped panel, controller dialogs and both Bridge settings entry points were verified on the development HA installation. The panel reuses Home Assistant frontend components; compatibility with future HA frontend changes is not guaranteed.

Update through HACS, **restart Home Assistant and fully refresh the browser**. No separate panel installation is needed. All v0.9.0 compatibility notes, including Adaptive Lighting group limitations and native Hue transition reporting, still apply.

## Česky

Nový seskupený přehled v postranním panelu: Bridge → Dial / Button / Dimmer / Motion → nastavení konkrétního ovladače. Ozubené kolečko u Bridge otevře hlavní nastavení přímo nad panelem. Původní stránka integrace i její nastavení zůstávají dostupné. Formuláře Buttonu, Dimmeru a Dialu mají sjednocené přepínače, výběry a posuvníky. Nastavené hodnoty ani chování ovladačů se nemění. Po aktualizaci restartuj HA a obnov celou stránku prohlížeče. Panel se zpřístupní automaticky administrátorům.

---

# v0.9.0 — Motion schedules, shared control conditions and Adaptive Lighting cooperation

**Pre-release / experimental.** Requires Home Assistant 2026.10.1+, Hue v2 Bridge and the official Hue integration.

- Add Hue Motion control using official HA sensor events, without fast motion polling. New Motion rows start disabled; disable competing native Hue lighting rules before enabling them.
- Add adjacent time periods with independent brightness/color, absence timers, target overrides and Do not disturb. One period is All day. Already running cycles retain their original period settings.
- Add live lux preview, 650 lx / ∞ threshold, three-position movement sensitivity, and disabled-sensor warnings. Lux filtering is local; sensitivity writes occur only on enabled configuration saves.
- Add three final-30-second ending styles, 0.5 s startup/recovery and 2 s final-off transitions. Endings use actual pre-ending brightness. Persist the pre-ending level to prevent repeated brightness halving across cycles; saving Motion settings replaces the old cycle.
- Add independent Motion arrival/departure/manual-action policies and touched-light versus whole-group handover. Manual provenance covers only controls configured in this integration.
- Add a shared optional entity-state condition, independently selectable for Motion, Button, Dial and Dimmer. Allowed states are typed manually. Blocked motion cannot extend existing cycles; those can finish normally. Unknown/unavailable sources cannot grant control.
- Add opt-in Adaptive Lighting cooperation using its public manual-control service, matching group members and all relevant profiles. Partial targets of an unexpanded AL group are skipped with a warning: control the whole group or enable `expand_light_groups`. Existing manual flags are preserved; no AL settings are changed automatically. Works without AL installed.
- Use explicit on/off services for ordinary light toggles to avoid the AL toggle interception observed in testing. Add optional independent main Dial targets while retaining button-1 inheritance by default.
- Unify form switches, outlined selections and sliders. Localize polling choices, reveal numeric fields only in Continuous mode and explain the additional traffic/load. Refresh the browser after updating.
- Bundle the selected dark logo as local integration brand assets.

Validation: **273 tests**, Ruff lint/format and frontend JavaScript syntax checks. Hardware behavior remains device-dependent; this is not a physical scalability certification. Native Hue transitions may report the target/off state before the physical fade completes. RDM005 and all possible group/AL combinations have not been physically validated. An earlier external drop to approximately 8% remains unexplained; this release does not claim an upstream fix.

Update through HACS, **restart Home Assistant and refresh the browser**. The shared condition and AL cooperation are opt-in. Keep the official Hue integration loaded. Public release notes and README describe group limitations and AL interaction details.

---

## Česky

Předběžná verze přidává Motion s časovými bloky, třemi styly dohasnutí a uložením jasu před ztlumením. Obsahuje volitelnou spolupráci s Adaptivním osvětlením, společnou podmínku podle stavu entity se samostatným výběrem typů ovladačů a sjednocené formuláře. Po instalaci restartuj HA a obnov stránku. Před zapnutím Motionu vypni souběžné pravidlo ovládání světel v Hue. U AL skupin bez rozbalení členů je potřeba ovládat celou skupinu nebo zapnout `expand_light_groups`.
