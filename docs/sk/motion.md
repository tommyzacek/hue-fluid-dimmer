# Motion

[Čeština](../cs/motion.md) | [Slovenština](../sk/motion.md) | [English](../en/motion.md)

[Všetky návody](README.md) · [Bridge a Adaptive Lighting](bridge.md)

Motion rozsvieti vybrané svetlá pri pohybe a po čase bez pohybu ich podľa nastavenia zhasne. Pohyb a osvetlenie preberá z oficiálnej Hue integrácie, nepridáva rýchly polling pohybového senzora.

<p align="center">
  <img src="../assets/screenshots/motion.png" alt="Ukážka formulára nastavenia" width="420">
</p>

## Prvé nastavenie

1. Otvorte **Hue Reconfigo → Bridge → Motion → váš senzor**.
2. Vyberte cieľové svetlá alebo skupinu.
3. Nastavte citlivosť na svetlo a pohyb.
4. V **Celý deň** nastavte jas, farbu a čas bez pohybu.
5. Vyberte štýl zhasnutia a správanie pri inom ovládaní.
6. Vypnite konkurenčné svetelné pravidlo v Hue, zapnite naše ovládanie a uložte.

Oficiálne senzory a integráciu Hue ponechajte dostupné. Formulár upozorní na vypnutý oficiálny pohybový alebo svetelný senzor. Vypnutie nášho ovládania nevypne oficiálny senzor.

## Citlivosť na svetlo a pohyb

| Pole | Význam |
| --- | --- |
| **Citlivosť na svetlo** | Nové rozsvietenie je povolené pod vybranou hodnotou. Rozsah končí pri 650 lx; nasledujúca krajná poloha **∞** ruší obmedzenie osvetlením. |
| **Aktuálne osvetlenie** | Priebežné meranie a výsledok prahu ZAPNÚ/NEZAPNÚ. Ide o svetelnú podmienku; ovládanie môže blokovať aj Nerušiť, spoločná podmienka či vypnutá funkcia. |
| **Citlivosť na pohyb** | Nízka / Stredná / Vysoká menia citlivosť fyzického senzora. |

Pri konečnom prahu musí byť meranie platné a nižšie než prah. Rovnosť rozsvietenie nepovolí. Vypnutý alebo nedostupný svetelný senzor nepovolí nové rozsvietenie s konečným prahom. Už svietiace svetlá však môžu vstúpiť do cyklu a neskôr zhasnúť podľa politiky.

Prah osvetlenia vyhodnocujeme lokálne, pravidlo v Bridge neprepisujeme. Citlivosť na pohyb sa zapisuje do Bridge pri uložení zapnutého ovládania, môže teda ovplyvniť detekciu využívanú aj inde.

## Vyhradené časy

Jediný blok sa volá **Celý deň** a nemá upraviteľný začiatok. Pridaním ďalšieho rozdelíte deň: zadáte začiatok každého a koniec určí nasledujúci blok. Posledný nadväzuje cez polnoc na prvý. Platí miestny čas HA a začiatky sa nesmú opakovať.

| Príklad bloku | Jas a farba | Čas bez pohybu |
| --- | --- | --- |
| 07:00–23:00 | 80 %, biela 4000 K | 5 minút |
| 23:00–07:00 | 15 %, biela 2300 K | 1 minúta |

Každý blok má vlastný jas, farbu, časovač, prípadný iný výber svetiel a **Nerušiť**. Citlivosti, štýl zhasnutia a správanie pri ovládaní sú spoločné pre celý Motion.

**Nerušiť** nezačína nové cykly. Cyklus z predchádzajúceho bloku sa dokončí podľa pôvodného nastavenia, vrátane predlžovania pohybom a návratu jasu zo záverečného stlmenia. Prechod medzi blokmi sám nezmení svietiace svetlá.

### Jas a farba pri začatí

- **Jas → Nastavené %** pošle zadanú úroveň.
- **Jas → Predchádzajúci stav** obnoví uložený jas pred vlastným záverečným stlmením. Bráni opakovanému poleniu 100 → 50 → 25 % medzi cyklami. Bez uloženej hodnoty jas neposiela.
- **Farba → Ponechať bez zmeny** neposiela farbu. Ďalšie voľby sú teplota bielej a vlastná farba pre podporované svetlá.

Pamäť jasu neobnovuje farbu a nie je históriou všetkých externých zmien. Zmena počas cyklu sa zohľadní pri snímke pred záverečným stlmením. Novšie rozsvietenie iným spôsobom zo stavu vypnuté zneplatní starý uložený jas, aby neskoršie zapnutie neprepísalo novú hodnotu starou. Farba sa nastavuje samostatne.

## Cyklus a časovač

Prvý prijatý pohyb začne cyklus. Motion vykoná zapnutie podľa pravidiel pre už svietiace svetlá. **Čas bez pohybu začne plynúť až po tom, čo senzor oznámi pokoj.** Pri nepretržitom hlásení pohybu svetlá pre tento časovač nezhasnú.

Nový pohyb časovač preruší. Po ďalšom pokoji začne celý nastavený čas znovu. Bežné obnovenie neopakuje počiatočný jas/farbu. Ak začalo záverečné stlmenie, vráti jeho uložený východiskový jas.

Posuvník ponúka **1–10 minút po polminútach**, potom celé minúty do **60 minút**. Uloženie zmenenej konfigurácie Motionu zruší starý cyklus; jeho odpočet sa neprenáša do nového nastavenia.

### Pozvoľné zhasnutie

Začína posledných **30 sekúnd** odpočtu. Každé svetlo používa vlastný aktuálny jas zo začiatku stlmenia.

| Štýl | Posledných 30 sekúnd |
| --- | --- |
| Plynulé stlmenie na 50 % | Počas 30 s dosiahne polovicu východiskového jasu, potom sa vypne. |
| Plynulé dohasnutie | Počas 30 s postupne zhasína k nule. |
| Rýchle stlmenie na 50 % a vypnutie | Počas 2 s dosiahne polovicu, počká a na konci sa vypne. |

Príklad: Motion rozsvieti na 100 %, vy znížite na 60 %. Záverečná polovica znamená **30 %**, nie 50 %. Návrat pri pohybe obnoví **60 %**.

Počiatočné rozsvietenie a návrat používajú prechod **0,5 s**, konečné vypnutie **2 s**. Bez pozvoľného zhasnutia ostane jas do konca odpočtu, potom sa pošle vypnutie s týmto prechodom.

Hue môže do HA okamžite nahlásiť cieľový jas/vypnutie, hoci fyzicky ešte beží rampa. Stav ani história HA potom nemerajú skutočný okamžitý jas. Integrácia údaj umelo neprepisuje odhadom.

## Svetlá, ktoré už svietia pri príchode

Tieto dve polia platia len pre svetlá svietiace pred začiatkom cyklu. Členy jednej skupiny sa preto môžu správať odlišne.

| Pole | Voľba | Výsledok |
| --- | --- | --- |
| Pri prvom pohybe | Použiť nastavený jas a farbu zo sekcie „Vyhradené časy“ | Na začiatku použije aktuálny blok, ak to dovolí svetelná podmienka. |
| Pri prvom pohybe | Ponechať aktuálny jas a farbu | Nechá vzhľad a zahrnie svetlo do cyklu. |
| Po uplynutí času bez pohybu | Zhasnúť aj tieto svetlá | Automatické zhasnutie zahŕňa pôvodne svietiace svetlá. |
| Po uplynutí času bez pohybu | Nechať ich svietiť | Pôvodne svietiace svetlá neovplyvní záverečnou rampou ani vypnutím. |
| Po uplynutí času bez pohybu | Vrátiť jas a farbu z okamihu príchodu | Na konci im vráti zachytený pôvodný vzhľad. |

Príklad: lampa svieti na 40 %, strop je vypnutý. Ponechať aktuálny jas/farbu + Nechať ich svietiť ponechá lampu na 40 %, rozsvieti strop a na konci zhasne len strop.

## Zásah ovládačom

**Platí iba pre ovládače nastavené v Hue Reconfigo. Zmeny z aplikácií ani iných automatizácií sa nepovažujú za zásah ovládačom.** Externá zmena môže ovplyvniť jas pre záverečnú rampu, sama však neaktivuje odovzdanie ovládania.

### Má Motion po ručnej zmene jasu alebo farby automaticky zhasnúť?

| Voľba | Príklad: Motion ovláda lampu a strop, ovládačom zmeníte lampu |
| --- | --- |
| **Áno, všetky svetlá** | Zmena zostane, časovač pokračuje a obe zhasnú podľa ostatných pravidiel. Ďalší bežný pohyb nevynúti počiatočný jas/farbu. |
| **Nie, žiadne svetlá** | Celý aktuálny výber Motionu sa odovzdá používateľovi. Jas stropu sa nezmení, ale ani automaticky nezhasne. |
| **Iba svetlá, ktoré neboli ručne ovládané** | Lampa sa odovzdá používateľovi, strop ďalej zhasne podľa cyklu. |

Voľby neurčujú jas/farbu pri zásahu, ale ktoré svetlá ďalej riadi Motion. Samostatné pravidlo pre svetlá svietiace už pri príchode naďalej platí.

Plné ovládanie odovzdaných svetiel sa obnoví až po **ich vypnutí, dokončení pôvodného cyklu a novej detekcii pohybu**. Nie je tu časovač návratu. Samotný uplynulý čas ani pokoj senzora ich neprevezme. Pokiaľ senzor hlási pohyb, pôvodný cyklus ešte nemusel dokončiť odpočet.

### Keď ovládačom zhasnem

| Voľba | Výsledok pre vypnuté svetlá |
| --- | --- |
| **Ďalší pohyb smie znovu hneď rozsvietiť** | Nasledujúca nová detekcia ich môže vrátiť do bežiaceho cyklu. |
| **Ponechať zhasnuté do skončenia aktuálneho cyklu** | Pohyb ich v tomto cykle nerozsvieti. Nový cyklus ich môže prevziať. |

„Hneď“ znamená pri ďalšej novej udalosti pohybu. Pri nepretržitom pohybe integrácia nevytvára umelú detekciu. Pravidlo platí pre skutočne vypnuté svetlá, nerozširuje sa automaticky na celú miestnosť.

## Tri praktické zostavy

| Cieľ | Už svietiace pri príchode | Po odpočte | Po ručnej zmene |
| --- | --- | --- | --- |
| Chodba: Motion všetko obslúži | Použiť nastavenia bloku | Zhasnúť aj tieto svetlá | Áno, všetky svetlá |
| Obývačka: rešpektovať lampu | Ponechať aktuálny jas/farbu | Nechať ich svietiť | Iba svetlá, ktoré neboli ručne ovládané |
| Miestnosť: ručnou zmenou prevziať všetko | Podľa potreby | Podľa potreby | Nie, žiadne svetlá |

Pri neprítomnosti použite [spoločnú podmienku entity](bridge.md#blokovať-správanie-entitou) a zahrňte Motion. Platí samostatne vo všetkých časových blokoch.
