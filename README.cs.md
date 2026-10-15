# Hue Fluid Dimmer

[Čeština](README.cs.md) | [Slovenčina](README.sk.md) | [English](README.md)

*Plynulé stmívání. Nízká latence.*

Experimentální doplněk Home Assistantu pro Philips Hue **Tap Dial**, **Smart Button**, **Dimmer v2** a **pohybové senzory**. Akce, cíle, jas a barvu nastavíte přímo v integraci, bez automatizací pro každý ovladač a bez duplicitních entit ovladačů.

Vyžaduje **Home Assistant 2026.10.1 nebo novější**, Hue Bridge s API v2 a nastavenou oficiální integraci **Philips Hue**. Projekt je nezávislý na Signify a Home Assistantu. Dokumentace sleduje aktuální vývoj; rozsah konkrétní nainstalované verze najdete v poznámkách k vydání.

## Uživatelské návody

| Skupina | Návod |
| --- | --- |
| Bridge | [Instalace, společné podmínky, Adaptive Lighting a polling](docs/cs/bridge.md) |
| Dial | [Předvolby kolečka, čtyři tlačítka a dočasné převzetí](docs/cs/dial.md) |
| Button | [Krátký/dlouhý stisk, dvojklik a trojklik](docs/cs/button.md) |
| Dimmer | [ON/OFF, +, − a HUE na Dimmeru v2](docs/cs/dimmer.md) |
| Motion | [Časové bloky, citlivost na světlo, časovač a ruční zásah](docs/cs/motion.md) |
| Společné akce | [Zapnutí, jas, barva, držení, ventilátory a skripty](docs/cs/akce-tlacitek.md) |

Začněte částí [Než začnete](docs/cs/README.md#než-začnete). Návody obsahují příklady a vysvětlují souvislosti mezi volbami.

## Rychlá instalace

1. Do HACS přidejte `https://github.com/tommyzacek/hue-fluid-dimmer` jako vlastní repozitář typu **Integration**.
2. Stáhněte vydání a restartujte Home Assistant.
3. V **Nastavení → Zařízení a služby** přidejte **Hue Fluid Dimmer** a vyberte existující Hue Bridge.
4. V Hue nastavte příslušenství na **Konfigurovat v jiné aplikaci**. Vypněte konkurenční automatizace pro stejné vstupy; oficiální Hue integraci ponechte zapnutou.
5. Jako správce otevřete boční panel **Hue Fluid Dimmer**. Vyberte ovladač, nastavte cíle/akce a zapněte ovládání. Kolo vedle Bridge otevře společná nastavení. Po aktualizacích obnovte stránku.

Při ruční instalaci zkopírujte `custom_components/hue_fluid_dimmer` do `custom_components` konfigurace HA a restartujte. Boční panel je součástí, neinstaluje se zvlášť.

## Podporovaná zařízení

| Typ | Rozsah |
| --- | --- |
| Tap Dial | Nalezené rotační prostředky a čtyři tlačítka |
| Smart Button | ROM001, RDM003, RDM005 |
| Dimmer v2 | RWL022; Dimmer v1 a nástěnné moduly nejsou zahrnuté |
| Hue Motion | Nalezené pohybové služby; vyžadují oficiální senzorové entity HA |

Nové ovladače začínají vypnuté. Cíle tlačítek mohou být světla/skupiny, ventilátory, vhodné číselné entity nebo jeden skript; regulace vyžaduje procentní cíle. Přímé cyklování scén není zahrnuté. Mapování RDM005 neznamená fyzické ověření každé funkce.

## Vývoj a omezení

Rozhraní podporuje češtinu, slovenštinu a angličtinu podle profilu HA. Pro ostatní jazyky se použije angličtina.

Nativní přechody Hue mohou nahlásit cílový stav před dokončením fyzické rampy. Plynulost a odezva závisejí na zařízeních a síti. Syntetické testy nenahrazují fyzické ověření.

[Technické poznámky a vývoj](docs/development.md) jsou anglicky a obsahují testování, podrobnosti připojení a historické pozorování toggle s Adaptive Lighting. CI spouští testy, Ruff, hassfest a HACS.
