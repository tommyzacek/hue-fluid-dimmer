# Uživatelské návody

[Čeština](../cs/README.md) | [Slovenčina](../sk/README.md) | [English](../en/README.md)

| Co chcete nastavit | Návod |
| --- | --- |
| Instalaci, společné podmínky, Adaptive Lighting a polling | [Bridge a společné nastavení](bridge.md) |
| Kolečko a čtyři tlačítka Tap Dial | [Dial](dial.md) |
| Jednotlačítkový ovladač | [Button](button.md) |
| Dimmer v2 s tlačítky ON/OFF, +, − a HUE | [Dimmer](dimmer.md) |
| Pohybové rozsvěcení, časové bloky a zhasínání | [Motion](motion.md) |
| Význam akcí, jasu, barvy a dlouhého držení | [Společné akce tlačítek](akce-tlacitek.md) |

## Než začnete

Hue Fluid Dimmer vyžaduje Home Assistant **2026.10.1 nebo novější**, Hue Bridge s API v2 a nastavenou oficiální integraci **Philips Hue**. Její zařízení ani entity nenahrazuje. Vlastní panel se přidá automaticky a je dostupný správcům HA.

**Adaptive Lighting je volitelná integrace z HACS**, nikoli součást oficiální Hue integrace. Bez ní Hue Fluid Dimmer normálně funguje. Pokud ji používáte, můžete zapnout [spolupráci v nastavení Bridge](bridge.md#spolupráce-s-adaptive-lighting).

V postranním panelu otevřete **Hue Fluid Dimmer → váš Bridge → skupinu ovladačů → konkrétní zařízení**. Nové ovladače mají ovládání vypnuté. Nastavení se uplatní po odeslání formuláře.

Příslušenství, které přebírá Hue Fluid Dimmer, nastavte v aplikaci Hue na **„Konfigurovat v jiné aplikaci“**, aby jej současně neovládala i aplikace Hue. Pro stejné vstupy vypněte také případné blueprinty a automatizace. Dva nezávislé systémy mohou jinak současně měnit jas, barvu nebo napájení. Oficiální integraci Philips Hue v Home Assistantu ponechte zapnutou.

Po aktualizaci restartujte HA a obnovte stránku prohlížeče, aby se načetly nové formuláře. Jazyk rozhraní se řídí profilem HA: čeština, slovenština, jinak angličtina. Tyto návody používají české názvy polí.

## Doporučený první test

Začněte jedním ovladačem a jedním světlem. Ověřte zapnutí, vypnutí a regulaci, potom přidejte skupinu světel a další stisky. U Motionu vyzkoušejte celý cyklus včetně odchodu, závěrečného ztlumení a návratu během něj. Skutečnou plynulost posuzujte na světle: údaj HA během přechodu může ukazovat už cílovou hodnotu.
