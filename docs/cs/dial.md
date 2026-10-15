# Tap Dial

[Čeština](../cs/dial.md) | [Slovenčina](../sk/dial.md) | [English](../en/dial.md)

[Všechny návody](README.md) · [Společné akce tlačítek](akce-tlacitek.md)

Tap Dial má otočné kolečko a čtyři tlačítka. Kolečko reguluje procentní hodnotu, tlačítka mají samostatné akce pro jednotlivé stisky.

## Hlavní cíl kolečka

Otevřete **Hue Fluid Dimmer → Bridge → Dial → váš ovladač**. Standardně kolečko používá cíle krátkého stisku tlačítka 1. Chcete-li kolečkem ovládat například celou místnost, ale tlačítkem 1 jen její část, zapněte vlastní výběr cíle kolečka a zvolte širší skupinu.

Hlavní cíl musí být regulovatelný: světla, ventilátory nebo odpovídající číselné entity. Skript nemá průběžnou procentní hodnotu a cílem kolečka být nemůže. Pro jeden výběr používejte světla, nebo kompatibilní ostatní procentní entity.

## Rychlost a plynulost

| Předvolba | Citlivost světel | Přechod světel | Citlivost ostatních entit | Rampa ostatních entit |
| --- | --- | --- | --- | --- |
| Jemné | 1,2 | 1 s | 0,75 | 1 s |
| Vyvážené | 2,4 | 1 s | 1,5 | 0,75 s |
| Svižné | 4,8 | 0,5 s | 3 | 0,5 s |
| Vlastní | Vlastní hodnota | Vlastní hodnota | Vlastní hodnota | Vlastní hodnota |

Citlivost je základní změna v procentních bodech na 15 kroků hlášených Bridge. Není to zaručená změna na jeden fyzický zářez.

Všechny tři předvolby mají zapnuté adaptivní chování: pomalé otáčení umožňuje jemné úpravy, rychlé otáčení výraznější změnu. Vlastní nastavení obsahuje oddělené sekce **Světla** a **Ostatní entity**, každou s citlivostí a přechodem/rampou, plus přepínač adaptivního chování. Vlastní hodnoty zůstávají uložené při přepnutí na předvolbu.

Vyšší citlivost mění větší část rozsahu stejným pohybem. Kratší přechod rychleji dosáhne cíle, ale může zvýraznit kroky. Začněte Vyváženým a měňte vždy jednu hodnotu. Nastavení mění odezvu příkazů, nikoli rychlost příchodu události z ovladače.

Světla používají přechody podporované svou integrací; ostatní entity softwarovou rampu přes služby HA. Krok a skutečná plynulost závisejí na zařízení. Při změně směru se zahodí rozpracované budoucí cíle původního směru. Hodnota přechodu s adaptivním chováním není pevně zaručená délka každé jednotlivé změny.

## Dočasné převzetí kolečka

U **kteréhokoli typu stisku tlačítek 2, 3 a 4** lze vybrat akci dočasného převzetí dialu. Vyberte cíle přímo u tohoto stisku. Krátký stisk stejného tlačítka může zůstat vypnutý nebo ovládat něco jiného.

Příklad:

1. Hlavní kolečko ovládá kuchyňská světla.
2. Na tlačítku 2 zapnete dvojklik, vyberete ventilátor a akci převzetí dialu.
3. Dvojklik přesměruje kolečko na ventilátor. Sám ventilátor nezapíná běžnou tlačítkovou akcí.
4. Otočením měníte výkon podle nastavení **Ostatní entity**.
5. Po **5 sekundách od posledního otočení** se kolečko vrátí k hlavnímu cíli. Pokud po převzetí vůbec neotočíte, vrátí se po **5 sekundách od převzetí**.

Převzetí nepřepisuje trvalé nastavení a nevrací ventilátor na původní výkon. Mění jen to, co dočasně ovládá kolečko. Puštění tlačítka neukončuje toto přesměrování; jeho konec se řídí uvedenými časy. Volba není dostupná na tlačítku 1 ani na samostatném Buttonu nebo Dimmeru.

Ostatní akce všech čtyř tlačítek včetně jasu, barvy a regulace držením popisují [společné akce](akce-tlacitek.md). Polling a společné podmínky najdete v [nastavení Bridge](bridge.md).
