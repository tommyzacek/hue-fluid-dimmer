# Dimmer v2

[Čeština](../cs/dimmer.md) | [Slovenština](../sk/dimmer.md) | [English](../en/dimmer.md)

[Všetky návody](README.md) · [Spoločné akcie tlačidiel](akce-tlacitek.md)

Návod platí pre **Hue Dimmer v2, model RWL022**. Dimmer v1 ani nástenné moduly nie sú súčasťou podpory.

| Pozícia | Tlačidlo | Obvyklé použitie |
| --- | --- | --- |
| 1, hore | ON/OFF | Zapnutie a vypnutie |
| 2 | + | Zvýšenie jasu |
| 3 | − | Zníženie jasu |
| 4, dole | HUE | Ďalšia nastavená akcia |

Symbol neurčuje funkciu napevno. Podporované stlačenia nastavíte vo formulári. HUE tu automaticky necykluje scény.

## Základné nastavenie

Otvorte **Hue Reconfigo → Bridge → Dimmer → váš ovládač**, vyberte predvolené ciele a nastavte tlačidlá. Nové nastavenia majú pre + a − pripravený krátky krok a dlhú reguláciu. Pred uložením ich skontrolujte; predtým uložené voľby sa môžu líšiť.

| Tlačidlo a stlačenie | Odporúčaná akcia | Výsledok |
| --- | --- | --- |
| ON/OFF krátko | Zapnutie / vypnutie | Zapne podľa jasu/farby alebo vypne. |
| + krátko | Zvýšiť o 10 percentuálnych bodov | Pridá 10 percentuálnych bodov. |
| + dlho | Plynulá regulácia pri držaní | Zvyšuje počas držania. |
| − krátko | Znížiť o 10 percentuálnych bodov | Uberie 10 percentuálnych bodov. |
| − dlho | Plynulá regulácia pri držaní | Znižuje počas držania. |
| HUE krátko | Iba zapnúť | Napríklad večerný jas a teplá biela. |

Pri dlhej regulácii + a − je smer pevný, nevyberá sa podľa prahov 30/60 %. Krok je dostupný pri krátkom stlačení týchto prostredných tlačidiel. Ostatné dlhé regulačné stlačenia používajú spoločné pravidlá smeru.

## Iný cieľ tlačidla HUE

Pre HUE zapnite **Použiť pre túto akciu iné než predvolené zariadenia** a vyberte napríklad ventilátor alebo jeden skript. Ostatné tlačidlá ďalej používajú predvolené svetlá. Rovnako možno oddeliť dvojklik a trojklik.

Ak pri rýchlom ON/OFF svetlo mení farby, overte, že Dimmer už nemá priradenie v Hue. Pôvodné akcie môžu súbežne meniť scény. Ďalším zdrojom zmien je AL; [spolupráca](bridge.md#spolupráca-s-adaptive-lighting) sa zapína v nastavení Bridge.

Jas, farbu, jednosmerné zapnutie/vypnutie a skripty opisuje [spoločný návod](akce-tlacitek.md).
