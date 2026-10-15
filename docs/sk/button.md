# Button

[Čeština](../cs/button.md) | [Slovenština](../sk/button.md) | [English](../en/button.md)

[Všetky návody](README.md) · [Spoločné akcie tlačidiel](akce-tlacitek.md)

Button má jedno fyzické tlačidlo. Integrácia rozlišuje krátke, dlhé stlačenie, dvojklik a trojklik. Podporované identifikátory sú ROM001, RDM003 a RDM005; podpora RDM005 vychádza z mapovania modelu, nie fyzického overenia všetkých funkcií.

## Základné nastavenie

1. Otvorte **Hue Reconfigo → Bridge → Button → váš ovládač**.
2. Vyberte **Predvolené svetlá / zariadenia**.
3. Zapnite požadované stlačenia a nastavte akcie.
4. Pre dlhé stlačenie možno zvoliť **Plynulú reguláciu pri držaní**.
5. Zapnite ovládanie a odošlite formulár.

Pred testom vypnite pôvodné akcie Buttonu v Hue. Súbeh môže vyvolávať scény alebo zmeny farieb zároveň s našimi akciami.

## Príklad: bežné a večerné svetlo

| Stlačenie | Akcia | Jas | Farba |
| --- | --- | --- | --- |
| Krátke | Zapnutie / vypnutie | Nastavené 70 % | Biela 4000 K |
| Dvojklik | Iba zapnúť | Nastavené 25 % | Biela 2300 K |
| Dlhé | Plynulá regulácia pri držaní | Podľa držania | Touto akciou sa nemení |
| Trojklik | Vypnutý | — | — |

Dvojklik zmení vzhľad aj svietiaceho svetla. Krátke stlačenie ho vypne. Po aktivovaní dvojkliku bude krátke stlačenie čakať na možné pokračovanie.

Iný cieľ len pre jedno stlačenie nastavíte cez **Použiť pre túto akciu iné než predvolené zariadenia**. Trojklik môže napríklad spúšťať skript a ostatné stlačenia ovládať svetlá.

Predchádzajúci jas, skupiny, reguláciu a skripty vysvetľujú [spoločné akcie](akce-tlacitek.md). Ak svetlá ovláda aj Motion, jeho reakciu nastavte v [zásahu ovládačom](motion.md#zásah-ovládačom).
