# Button

[Čeština](../cs/button.md) | [Slovenčina](../sk/button.md) | [English](../en/button.md)

[Všechny návody](README.md) · [Společné akce tlačítek](akce-tlacitek.md)

Button je ovladač s jedním fyzickým tlačítkem. Integrace rozlišuje krátký stisk, dlouhý stisk, dvojklik a trojklik. Podporované modelové identifikátory jsou ROM001, RDM003 a RDM005; podpora RDM005 vychází z mapování modelu, nikoli fyzického ověření všech funkcí.

## Základní nastavení

1. Otevřete **Hue Reconfigo → Bridge → Button → váš ovladač**.
2. Vyberte **Výchozí světla / zařízení**.
3. Zapněte požadované stisky a u každého nastavte akci.
4. Pro dlouhý stisk lze zvolit **Plynulou regulaci**.
5. Zapněte ovládání a odešlete formulář.

Před testem vypněte původní akce Buttonu v aplikaci Hue. Jejich souběh může vyvolávat scény nebo změny barev zároveň s akcemi integrace.

## Příklad: běžné a večerní světlo

| Stisk | Akce | Jas | Barva |
| --- | --- | --- | --- |
| Krátký | Zapnutí / vypnutí | Nastavené 70 % | Bílá 4000 K |
| Dvojklik | Pouze zapnout | Nastavené 25 % | Bílá 2300 K |
| Dlouhý | Plynulá regulace | Podle držení | Nemění se touto akcí |
| Trojklik | Vypnutý | — | — |

Dvojklik změní vzhled i rozsvíceného světla. Krátký stisk jej vypne. Po aktivaci dvojkliku bude vyhodnocení krátkého stisku čekat na možné pokračování.

Jiný cíl jen pro jeden stisk nastavíte přepínačem **Použít pro tuto akci jiná než výchozí zařízení**. Může tak například trojklik spouštět skript, zatímco ostatní stisky ovládají světla.

Význam předchozího jasu, chování skupin, regulaci i práci se skripty popisují [společné akce](akce-tlacitek.md). Pokud světla řídí také Motion, jeho reakci na Button nastavte v [chování Motionu](motion.md#zásah-ovladačem).
