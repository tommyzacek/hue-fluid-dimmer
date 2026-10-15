# Dimmer v2

[Čeština](../cs/dimmer.md) | [Slovenština](../sk/dimmer.md) | [English](../en/dimmer.md)

[Všechny návody](README.md) · [Společné akce tlačítek](akce-tlacitek.md)

Tento návod platí pro **Hue Dimmer v2, model RWL022**. Dimmer v1 ani nástěnné moduly nejsou součástí této podpory.

| Pozice | Tlačítko | Obvyklé použití |
| --- | --- | --- |
| 1, nahoře | ON/OFF | Zapnutí a vypnutí |
| 2 | + | Zvýšení jasu |
| 3 | − | Snížení jasu |
| 4, dole | HUE | Další vámi nastavená akce |

Symbol tlačítka neurčuje jeho funkci napevno. Jednotlivé podporované stisky můžete nastavit ve formuláři. Tlačítko HUE zde samo automaticky necykluje scény.

## Základní nastavení

Otevřete **Hue Reconfigo → Bridge → Dimmer → váš ovladač**, vyberte výchozí cíle a nastavte jednotlivá tlačítka. U nového nastavení mají + a − připravený krátký krok a dlouhou regulaci. Zkontrolujte je před uložením; dříve uložené vlastní volby se mohou lišit.

| Tlačítko a stisk | Doporučená akce | Výsledek |
| --- | --- | --- |
| ON/OFF krátce | Zapnutí / vypnutí | Zapne podle zvoleného jasu/barvy, nebo vypne. |
| + krátce | Zvýšit | Přidá 10 procentních bodů. |
| + dlouze | Plynulá regulace | Zvyšuje po dobu držení. |
| − krátce | Snížit | Ubere 10 procentních bodů. |
| − dlouze | Plynulá regulace | Snižuje po dobu držení. |
| HUE krátce | Pouze zapnout | Například nastaví večerní jas a teplou bílou. |

U dlouhé regulace tlačítek + a − je směr pevný; nevybírá se podle prahů 30/60 %. Přidávání a ubírání krokem je dostupné u krátkého stisku těchto prostředních tlačítek. Ostatní dlouhé stisky s regulací používají společná pravidla směru.

## Jiný cíl tlačítka HUE

Pro HUE můžete zapnout **Použít pro tuto akci jiná než výchozí zařízení** a zvolit například ventilátor nebo jeden skript. Zbylá tlačítka pak dál používají výchozí světla. Stejně lze oddělit i dvojklik a trojklik.

Pokud při rychlém ON/OFF světlo mění barvy, ověřte, že stejný Dimmer nemá stále přiřazené ovládání v Hue. Původní Hue akce může měnit scény souběžně. Dalším zdrojem změn může být AL; jeho [spolupráce](bridge.md#spolupráce-s-adaptive-lighting) se zapíná v hlavním nastavení Bridge.

Pro jas, barvu, jednosměrné zapnutí/vypnutí a skripty platí [společný návod](akce-tlacitek.md).
