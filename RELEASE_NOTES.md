# v1.0.0 — Hue Reconfigo

**Stable release.** Requires Home Assistant **2026.10.1+**, a Hue Bridge with API v2 and the official Philips Hue integration. Adaptive Lighting is optional and can be installed through HACS.

## English

Hue Fluid Dimmer becomes **Hue Reconfigo**. This release publishes the internally tested controller and Motion behavior, with the grouped administrator panel and complete guides in English, Czech and Slovak.

### Changes since 0.9.5

- Give light actions independent brightness and color settings across Button, Dimmer and Tap Dial: Previous state / Configured %, and unchanged / white temperature / custom color. Reuse pre-fade brightness recovery so Motion endings do not become the next startup level.
- Add **Turn on only** and **Turn off only**. Turn on only applies brightness/color even when a light is already on, making alternate appearances possible without toggling off. Fan/number targets retain percentage actions; scripts retain HA script execution semantics.
- Allow **temporary Dial takeover on every gesture of buttons 2–4**, using that gesture's own targets, even when short press is disabled. Keep both five-second return limits.
- Simplify Motion manual intervention into three choices: automatic shutdown for all lights, none, or only untouched lights. Remove the timed return option: handed-over lights resume only after off, completion of the original cycle and a new motion detection. Manual off remains separately configurable and affects the lights actually switched off.
- Fix the four family switches under the shared entity condition so they do not flicker or resist changes.
- Rename the displayed integration, HACS entry, panel, generated Bridge titles and documentation to Hue Reconfigo. Update links to the renamed repository. Preserve user-defined titles.
- Add matching README and guides for Bridge, Dial, Button, Dimmer, Motion and shared actions in all three languages, including optional Adaptive Lighting cooperation and group limitations.

### Update and compatibility

Update through HACS, **restart Home Assistant and refresh the browser**. Set managed accessories to **Configure in another app** in Hue and disable competing automations for the same inputs. Keep the official Hue integration enabled.

The technical domain and installation directory remain **`hue_fluid_dimmer`**. Existing controller settings are retained; no new pairing or integration recreation is required. The panel URL remains `/hue-fluid-dimmer` so existing bookmarks continue to work. The old GitHub repository URL redirects to the new one. Historical releases remain pre-releases.

Native Hue transitions may report their target brightness/off state before the physical fade finishes. Percentage smoothness depends on each target's supported steps and network response. AL cooperation cannot safely mark only some members of an unexpanded AL group: control the full group or use AL's `expand_light_groups`. An earlier external brightness drop to about 8% remains unexplained; this release does not claim a fix for that separate issue.

Validation: **358 tests**, Ruff lint/format and JavaScript syntax checks. Functional sources were compared against the running development HA installation; differences are the new branding, title compatibility, frontend cache versions and release metadata. Device-specific physical testing remains distinct from automated checks.

[English guides](https://github.com/tommyzacek/hue-reconfigo/tree/main/docs/en)

## Česky

**První stabilní vydání Hue Reconfigo**, dříve Hue Fluid Dimmer. Zveřejňuje verzi odladěnou v interní instalaci HA.

- Sjednocený jas a barva pro akce tlačítek Buttonu, Dimmeru i Dialu; jas před dohasnutím se obnovuje samostatně.
- Nové akce **Pouze zapnout / Pouze vypnout**. Pouze zapnout přenastaví vzhled i svítícího světla, aniž by jej vypnulo.
- Dočasné převzetí kolečka na každém typu stisku tlačítek 2–4 podle cíle daného stisku. Oba návratové limity zůstávají 5 sekund.
- Přehlednější zásah ovladačem u Motionu: automaticky zhasnout všechna / žádná / jen nedotčená světla. Návrat předaných světel až po vypnutí, dokončení původního cyklu a nové detekci. Samostatná volba reakce na ruční vypnutí.
- Opravené přepínače blokovaných skupin, nové jméno v panelu i HACS a kompletní návody ve třech jazycích.

Vyžaduje **HA 2026.10.1+**, Hue Bridge s API v2 a oficiální Hue integraci. **Adaptive Lighting je volitelné**. Aktualizuj přes HACS, restartuj HA a obnov prohlížeč. Příslušenství v Hue nastav na **Konfigurovat v jiné aplikaci**, aby se ovládání nezdvojovalo.

Technická doména a složka `hue_fluid_dimmer`, URL panelu i nastavení zůstávají zachované; nové párování není nutné. Vlastní názvy se nepřepisují. Starší vydání zůstávají předběžná. Při rampě může HA zobrazovat cílový stav dřív než světlo fyzicky dojede. U AL skupiny bez rozbalení členů je potřeba ovládat celou skupinu nebo použít `expand_light_groups`. Dřívější externí pokles na 8 % nemá potvrzenou příčinu a toto vydání netvrdí jeho opravu.

Ověření: **358 testů**, Ruff a syntaxe JavaScriptu. Funkční zdroje porovnané s běžící instalací HA; fyzické chování závisí také na zařízení.

[České návody](https://github.com/tommyzacek/hue-reconfigo/tree/main/docs/cs)

## Slovenčina

**Prvé stabilné vydanie Hue Reconfigo**, predtým Hue Fluid Dimmer. Zverejňuje verziu odladenú v internej inštalácii HA.

- Zjednotený jas a farba pre akcie Buttonu, Dimmeru aj Dialu; jas pred dohasnutím sa obnovuje samostatne.
- Nové akcie **Iba zapnúť / Iba vypnúť**. Iba zapnúť zmení vzhľad aj svietiaceho svetla bez vypnutia.
- Dočasné prevzatie kolieska pri každom type stlačenia tlačidiel 2–4 podľa cieľa daného stlačenia. Oba návratové limity ostávajú 5 sekúnd.
- Prehľadnejší zásah ovládačom pri Motione: automaticky zhasnúť všetky / žiadne / iba nedotknuté svetlá. Návrat odovzdaných svetiel až po vypnutí, dokončení pôvodného cyklu a novej detekcii. Samostatná reakcia na ručné vypnutie.
- Opravené prepínače blokovaných skupín, nové meno v paneli aj HACS a kompletné návody v troch jazykoch.

Vyžaduje **HA 2026.10.1+**, Hue Bridge s API v2 a oficiálnu Hue integráciu. **Adaptive Lighting je voliteľné**. Aktualizuj cez HACS, reštartuj HA a obnov prehliadač. Príslušenstvo v Hue nastav na **Konfigurovať v inej aplikácii**, aby sa ovládanie nezdvojovalo.

Technická doména a priečinok `hue_fluid_dimmer`, URL panelu aj nastavenia zostávajú zachované; nové párovanie netreba. Vlastné názvy sa neprepisujú. Staršie vydania zostávajú predbežné. Pri rampe môže HA zobrazovať cieľ skôr, než svetlo fyzicky dobehne. Pri AL skupine bez rozbalených členov ovládaj celú skupinu alebo použi `expand_light_groups`. Skorší externý pokles na 8 % nemá potvrdenú príčinu a toto vydanie netvrdí jeho opravu.

Overenie: **358 testov**, Ruff a syntax JavaScriptu. Funkčné zdroje porovnané s bežiacou inštaláciou HA; fyzické správanie závisí aj od zariadenia.

[Slovenské návody](https://github.com/tommyzacek/hue-reconfigo/tree/main/docs/sk)

---

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
