# Spoločné akcie tlačidiel

[Čeština](../cs/akce-tlacitek.md) | [Slovenčina](../sk/akce-tlacitek.md) | [English](../en/akce-tlacitek.md)

[Všetky návody](README.md) · [Button](button.md) · [Dimmer](dimmer.md) · [Dial](dial.md)

Krátke stlačenie, dlhé stlačenie, dvojklik a trojklik majú vlastné prepínače a nastavenia. Ponuka akcií závisí od ovládača, stlačenia a cieľov. Vypnuté stlačenie nevykonáva akciu.

## Akcie pre svetlá

| Akcia | Výsledok |
| --- | --- |
| **Zapnutie / vypnutie** | Ak niektoré vybrané svetlo svieti, výber vypne. Inak ho zapne podľa nastaveného jasu a farby. |
| **Iba zapnúť** | Vždy zapne a použije nastavený jas/farbu aj pri rozsvietenom svetle. Ďalším rovnakým stlačením nevypne. |
| **Iba vypnúť** | Vždy vypne. Nastavenia jasu a farby sa nepoužívajú. |
| **Plynulá regulácia pri držaní** | Len dlhé stlačenie: reguluje počas držania, uvoľnenie ju zastaví. |

Príklad dvoch farieb: krátke stlačenie Zapnutie / vypnutie, 70 %, 4000 K; dvojklik Iba zapnúť, 30 %, 2300 K. Dvojklik zmení vzhľad už svietiaceho svetla. Ak by aj dvojklik používal Zapnutie / vypnutie, svetlo by vypol.

### Jas a farba sú nezávislé

| Pole | Voľba | Význam |
| --- | --- | --- |
| Jas | **Predchádzajúci stav** | Použije uložený jas. Po záverečnom stlmení Motionu obnoví jas pred stlmením. Bez uloženej hodnoty jas neposiela a zapnutie nechá na svetle alebo jeho integrácii. |
| Jas | **Nastavené %** | Pri zapnutí pošle zadaný jas. |
| Farba svetla | **Ponechať bez zmeny** | Nepošle farbu ani teplotu bielej. |
| Farba svetla | **Teplota bielej** | Pošle kelviny v rámci možností svetla. Posuvník vyberá po stovkách kelvinov. |
| Farba svetla | **Vlastná farba** | Pošle vybranú farbu podporovaným svetlám. |

Predchádzajúci stav neobnovuje celú scénu ani farbu. Integrácia si pamätá jas pri vlastnom vypnutí a pred vlastným záverečným stlmením. Nie je to univerzálna história všetkých zmien vo všetkých aplikáciách. Nepodporovaná farba sa svetlu neposiela.

So zapnutou [spoluprácou s AL](bridge.md#spolupráca-s-adaptive-lighting) sa výslovne zadaný jas a farba označujú ako ručné parametre. Ponechanie farby bez zmeny samo neurčuje, či ju AL neskôr upraví.

## Ciele akcie

Button a Dimmer majú hore **Predvolené svetlá / zariadenia**. Stlačenie ich použije automaticky. Pre výnimku zapnite **Použiť pre túto akciu iné než predvolené zariadenia** a vyberte vlastné ciele. Vypnutie výnimky vráti predvolený výber a zahodí pôvodný vlastný výber.

Tap Dial má ciele priamo pri jednotlivých stlačeniach. Prevzatie kolieska používa výber konkrétneho stlačenia, ktoré ho vyvolalo.

Podporované sú svetlá/skupiny, ventilátory `fan`, číselné entity `number` alebo jeden skript. Priamy výber a cyklovanie scén nie sú súčasťou ponuky; vlastnú postupnosť možno riešiť skriptom. Pri bežnej akcii nemiešajte rôzne domény entít. Regulácia vyžaduje kompatibilné percentuálne ciele.

## Ventilátory a číselné entity

| Voľba | Pri zapnutí |
| --- | --- |
| Zapnutie / vypnutie | Ventilátor použije bežné zapnutie; číselný cieľ prejde na hornú hranicu. |
| Vypnuté / predchádzajúce percento | Vráti nenulovú hodnotu uloženú pri vypnutí integráciou. Bez nej sa ventilátor bežne zapne; pri číselnom cieli sa výkon neodhaduje a zapíše sa upozornenie do logu. |
| Vypnuté / nastavené percento | Nastaví zadané percento. |
| Iba zapnúť | Nastaví zadané percento aj pri bežiacom zariadení. |
| Iba vypnúť | Nastaví nulu percent rozsahu. |

Pri `number` sa 0–100 % prepočíta na rozsah `min`–`max` a rešpektuje `step`. **0 % teda znamená minimum entity, ktoré nemusí byť fyzické vypnutie.** Pri PWM ventilátore overte, že minimum znamená zastavenie. Skutočný počet rýchlostí môže byť menší než sto.

## Dlhé podržanie

**Plynulá regulácia pri držaní** začne pri rozpoznaní dlhého stlačenia. Uvoľnenie ju zastaví. Smer sa vyberie na začiatku:

- pod 30 % nahor;
- nad 60 % nadol;
- medzi týmito hodnotami opačne než predchádzajúce podržanie; prvé nahor.

Na krajnej hodnote regulácia čaká na uvoľnenie, počas jedného podržania sa neobracia. + a − Dimmeru majú pevné smery. Hue svetlá môžu používať priame relatívne stmievanie s príkazom stop, ostatné zariadenia služby HA. Viditeľný dobeh závisí aj od zariadenia a spojenia.

## Dvojklik a trojklik

Bez aktívnych viacnásobných stlačení sa krátke stlačenie vyhodnotí pri uvoľnení bez čakania. Po ich zapnutí musí integrácia čakať na možné pokračovanie. Rozlišovanie používa interval **350 ms** a časové značky Bridge; prenos môže pridať oneskorenie. Klikajte prirodzene rýchlo, netreba odmeriavať presnú medzeru.

## Skripty

Vyberte jednu entitu `script`. Bežná akcia ju spustí cez `script.turn_on`; ďalšie stlačenie ju automaticky nevypne ako svetlo. Opakované spustenie určuje režim skriptu (`single`, `restart`, `queued`, `parallel`). **Iba vypnúť** volá `script.turn_off` a môže prerušiť čakajúce kroky. Pri zámku alebo inej dôležitej akcii s tým počítajte. Na samotné spúšťanie je zrozumiteľná voľba Iba zapnúť.
