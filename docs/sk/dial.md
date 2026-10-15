# Tap Dial

[Čeština](../cs/dial.md) | [Slovenčina](../sk/dial.md) | [English](../en/dial.md)

[Všetky návody](README.md) · [Spoločné akcie tlačidiel](akce-tlacitek.md)

Tap Dial má otočné koliesko a štyri tlačidlá. Koliesko reguluje percentuálnu hodnotu, tlačidlá majú samostatné akcie pre jednotlivé stlačenia.

## Hlavný cieľ kolieska

Otvorte **Hue Reconfigo → Bridge → Dial → váš ovládač**. Koliesko štandardne používa ciele krátkeho stlačenia tlačidla 1. Ak má koliesko ovládať celú miestnosť a tlačidlo 1 len časť, zapnite vlastný výber cieľa kolieska a zvoľte širšiu skupinu.

Hlavný cieľ musí podporovať reguláciu: svetlá, ventilátory alebo vhodné číselné entity. Skript nemá priebežnú percentuálnu hodnotu a nemôže byť cieľom kolieska. V jednom výbere používajte svetlá alebo kompatibilné ostatné percentuálne entity.

## Rýchlosť a plynulosť

| Predvoľba | Citlivosť svetiel | Prechod svetiel | Citlivosť ostatných entít | Rampa ostatných entít |
| --- | --- | --- | --- | --- |
| Jemné | 1,2 | 1 s | 0,75 | 1 s |
| Vyvážené | 2,4 | 1 s | 1,5 | 0,75 s |
| Svižné | 4,8 | 0,5 s | 3 | 0,5 s |
| Vlastné | Vlastná hodnota | Vlastná hodnota | Vlastná hodnota | Vlastná hodnota |

Citlivosť je základná zmena v percentuálnych bodoch na 15 krokov hlásených Bridge. Nie je to zaručená zmena na jeden fyzický zárez.

Všetky tri predvoľby zapínajú adaptívne správanie: pomalé otáčanie umožní jemné úpravy, rýchle výraznejšiu zmenu. Vlastné nastavenie obsahuje sekcie **Svetlá** a **Ostatné entity**, každú s citlivosťou a prechodom/rampou, a adaptívny prepínač. Vlastné hodnoty sa zachovajú aj po výbere predvoľby.

Vyššia citlivosť zmení väčšiu časť rozsahu rovnakým pohybom. Kratší prechod rýchlejšie dosiahne cieľ, môže však zvýrazniť kroky. Začnite Vyváženým a meňte jednu hodnotu naraz. Nastavenie mení odozvu príkazov, nie rýchlosť príchodu udalosti z ovládača.

Svetlá používajú prechody svojej integrácie, ostatné entity softvérovú rampu cez služby HA. Krok a plynulosť závisia od zariadenia. Zmena smeru zahodí rozpracované budúce ciele pôvodného smeru. Pri adaptívnom správaní nie je hodnota prechodu pevne zaručenou dĺžkou každej zmeny.

## Dočasné prevzatie kolieska

Pri **ktoromkoľvek type stlačenia tlačidiel 2, 3 a 4** možno vybrať dočasné prevzatie dialu. Ciele vyberte priamo pri tomto stlačení. Krátke stlačenie toho istého tlačidla môže byť vypnuté alebo ovládať niečo iné.

Príklad:

1. Hlavné koliesko ovláda kuchynské svetlá.
2. Na tlačidle 2 zapnete dvojklik, vyberiete ventilátor a prevzatie dialu.
3. Dvojklik presmeruje koliesko na ventilátor. Sám nevykoná bežnú zapínaciu akciu tlačidla.
4. Otočením meníte výkon podľa **Ostatné entity**.
5. Po **5 sekundách od posledného otočenia** sa koliesko vráti na hlavný cieľ. Ak vôbec neotočíte, vráti sa po **5 sekundách od prevzatia**.

Prevzatie nemení trvalé nastavenia ani nevracia ventilátor na pôvodný výkon. Mení iba to, čo dočasne ovláda koliesko. Uvoľnenie tlačidla presmerovanie neukončí, rozhodujú časové limity. Voľba nie je dostupná na tlačidle 1 ani na samostatnom Buttone alebo Dimmeri.

Ostatné akcie, jas, farbu a držanie opisujú [spoločné akcie](akce-tlacitek.md). Polling a podmienky sú v [nastavení Bridge](bridge.md).
