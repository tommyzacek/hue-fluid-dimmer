# Používateľské návody

[Čeština](../cs/README.md) | [Slovenčina](../sk/README.md) | [English](../en/README.md)

| Čo chcete nastaviť | Návod |
| --- | --- |
| Inštaláciu, spoločné podmienky, Adaptive Lighting a polling | [Bridge a spoločné nastavenia](bridge.md) |
| Koliesko a štyri tlačidlá Tap Dial | [Dial](dial.md) |
| Jednotlačidlový ovládač | [Button](button.md) |
| Dimmer v2 s tlačidlami ON/OFF, +, − a HUE | [Dimmer](dimmer.md) |
| Rozsvietenie pohybom, časové bloky a zhasínanie | [Motion](motion.md) |
| Význam akcií, jasu, farby a dlhého podržania | [Spoločné akcie tlačidiel](akce-tlacitek.md) |

## Skôr než začnete

Hue Reconfigo vyžaduje Home Assistant **2026.10.1 alebo novší**, Hue Bridge s API v2 a nastavenú oficiálnu integráciu **Philips Hue**. Nenahrádza jej zariadenia ani entity. Vlastný panel sa pridá automaticky a je dostupný správcom HA.

**Adaptive Lighting je voliteľná integrácia z HACS**, nie súčasť oficiálnej Hue integrácie. Bez nej Hue Reconfigo normálne funguje. Ak ju používate, môžete zapnúť [spoluprácu v nastavení Bridge](bridge.md#spolupráca-s-adaptive-lighting).

V bočnom paneli otvorte **Hue Reconfigo → váš Bridge → skupinu ovládačov → zariadenie**. Nové ovládače majú ovládanie vypnuté. Nastavenia sa použijú po odoslaní formulára.

Príslušenstvo, ktoré preberá Hue Reconfigo, nastavte v aplikácii Hue na **„Konfigurovať v inej aplikácii“**, aby ho súčasne neovládala aj aplikácia Hue. Pre rovnaké vstupy vypnite aj prípadné blueprinty a automatizácie. Dva nezávislé systémy môžu inak súčasne meniť jas, farbu alebo zapnutie. Oficiálnu integráciu Philips Hue v Home Assistante ponechajte zapnutú.

Po aktualizácii reštartujte HA a obnovte stránku prehliadača, aby sa načítali nové formuláre. Jazyk rozhrania určuje profil HA: čeština, slovenčina, inak angličtina. Tieto návody používajú slovenské názvy polí.

## Odporúčaný prvý test

Začnite jedným ovládačom a jedným svetlom. Overte zapnutie, vypnutie a reguláciu, potom pridajte skupinu svetiel a ďalšie stlačenia. Pri Motione vyskúšajte celý cyklus vrátane odchodu, záverečného stlmenia a návratu počas neho. Plynulosť posudzujte na svetle: údaj HA počas prechodu môže ukazovať už cieľovú hodnotu.
