# Hue Reconfigo

[Čeština](README.cs.md) | [Slovenčina](README.sk.md) | [English](README.md)

*Centrum nastavenia Hue Tap Dial, Dimmer, Smart Button a pohybových senzorov v Home Assistante.*

Experimentálny doplnok Home Assistanta pre Philips Hue **Tap Dial**, **Smart Button**, **Dimmer v2** a **pohybové senzory**. Akcie, ciele, jas a farbu nastavíte priamo v integrácii, bez automatizácií pre každý ovládač a duplicitných entít ovládačov.

Vyžaduje **Home Assistant 2026.10.1 alebo novší**, Hue Bridge s API v2 a nastavenú oficiálnu integráciu **Philips Hue**. Projekt je nezávislý od Signify a Home Assistanta. Dokumentácia sleduje aktuálny vývoj; rozsah konkrétnej nainštalovanej verzie nájdete v poznámkach k vydaniu.

Oficiálna integrácia **Philips Hue** je potrebná. **Adaptive Lighting** je samostatná, voliteľná vlastná integrácia inštalovaná cez **HACS**. Ak ju používate, zapnite spoluprácu v nastavení Bridge v Hue Reconfigo, aby jej oznamoval ručné ovládanie jasu a farby. Hue Reconfigo funguje aj bez Adaptive Lighting.

Integrácia sa predtým volala **Hue Fluid Dimmer**. Technická doména aj priečinok zostávajú `hue_fluid_dimmer`, aby sa zachovali existujúce nastavenia. Nové párovanie nie je potrebné.

## Používateľské návody

| Skupina | Návod |
| --- | --- |
| Bridge | [Inštalácia, spoločné podmienky, Adaptive Lighting a polling](docs/sk/bridge.md) |
| Dial | [Predvoľby kolieska, štyri tlačidlá a dočasné prevzatie](docs/sk/dial.md) |
| Button | [Krátke/dlhé stlačenie, dvojklik a trojklik](docs/sk/button.md) |
| Dimmer | [ON/OFF, +, − a HUE na Dimmeri v2](docs/sk/dimmer.md) |
| Motion | [Časové bloky, citlivosť na svetlo, časovač a ručný zásah](docs/sk/motion.md) |
| Spoločné akcie | [Zapnutie, jas, farba, držanie, ventilátory a skripty](docs/sk/akce-tlacitek.md) |

Začnite časťou [Skôr než začnete](docs/sk/README.md#skôr-než-začnete). Návody obsahujú príklady a vysvetľujú súvislosti medzi voľbami.

## Rýchla inštalácia

1. Do HACS pridajte `https://github.com/tommyzacek/hue-reconfigo` ako vlastný repozitár typu **Integration**.
2. Stiahnite vydanie a reštartujte Home Assistant.
3. V **Nastavenia → Zariadenia a služby** pridajte **Hue Reconfigo** a vyberte existujúci Hue Bridge.
4. V Hue nastavte príslušenstvo na **Konfigurovať v inej aplikácii**. Vypnite konkurenčné automatizácie pre rovnaké vstupy; oficiálnu Hue integráciu ponechajte zapnutú.
5. Ako správca otvorte bočný panel **Hue Reconfigo**. Vyberte ovládač, nastavte ciele/akcie a zapnite ovládanie. Koliesko vedľa Bridge otvorí spoločné nastavenia. Po aktualizáciách obnovte stránku.

Pri ručnej inštalácii skopírujte `custom_components/hue_fluid_dimmer` do `custom_components` konfigurácie HA a reštartujte. Bočný panel je súčasťou, neinštaluje sa samostatne.

## Podporované zariadenia

| Typ | Rozsah |
| --- | --- |
| Tap Dial | Nájdené rotačné prostriedky a štyri tlačidlá |
| Smart Button | ROM001, RDM003, RDM005 |
| Dimmer v2 | RWL022; Dimmer v1 a nástenné moduly nie sú zahrnuté |
| Hue Motion | Nájdené pohybové služby; vyžadujú oficiálne senzorové entity HA |

Nové ovládače začínajú vypnuté. Cieľmi tlačidiel môžu byť svetlá/skupiny, ventilátory, vhodné číselné entity alebo jeden skript; regulácia vyžaduje percentuálne ciele. Priame cyklovanie scén nie je zahrnuté. Mapovanie RDM005 neznamená fyzické overenie každej funkcie.

## Vývoj a obmedzenia

Rozhranie podporuje češtinu, slovenčinu a angličtinu podľa profilu HA. Pre ostatné jazyky sa použije angličtina.

Natívne prechody Hue môžu nahlásiť cieľový stav pred dokončením fyzickej rampy. Plynulosť a odozva závisia od zariadení a siete. Syntetické testy nenahrádzajú fyzické overenie.

[Technické poznámky a vývoj](docs/development.md) sú v angličtine a obsahujú testovanie, pripojenie a historické pozorovanie toggle s Adaptive Lighting. CI spúšťa testy, Ruff, hassfest a HACS.
