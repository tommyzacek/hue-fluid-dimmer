# Bridge a společné nastavení

[Čeština](../cs/bridge.md) | [Slovenčina](../sk/bridge.md) | [English](../en/bridge.md)

[Všechny návody](README.md)

## Instalace a otevření nastavení

1. V HACS přidejte `https://github.com/tommyzacek/hue-fluid-dimmer` jako vlastní repozitář typu **Integration**.
2. Stáhněte požadované vydání a restartujte Home Assistant. Pro předběžná vydání povolte jejich zobrazování v HACS.
3. V **Nastavení → Zařízení a služby → Přidat integraci** vyberte Hue Fluid Dimmer a existující Hue Bridge.
4. Otevřete postranní panel **Hue Fluid Dimmer**. Ovladače jsou rozdělené na Dial, Button, Dimmer a Motion.

Ozubené kolo vedle názvu Bridge otevře společné nastavení přímo v panelu. Zůstává dostupné i standardní nastavení integrace v Zařízení a služby. Panel nevyžaduje samostatnou instalaci, nevytváří další Bridge ani duplicitní entity a sám nepřidává pravidelné dotazování.

## Blokovat chování entitou

Tato funkce vznikla z potřeby zabránit automatickému rozsvěcení v prázdné domácnosti. Pohyb může zaznamenat senzor i kvůli zvířeti, nechtěnému podnětu nebo při neoprávněném vstupu — a v takové situaci nemusí být žádoucí rozsvítit. Pokud už máte v HA entitu určující stav domácnosti, můžete na ni ovládání navázat: například povolit Motion jen ve stavu „doma“ a ruční ovladače ponechat funkční. Stejný princip lze použít i pro jiné vlastní podmínky, bez závislosti na konkrétním systému přítomnosti.

Tato volba dovolí ovládání jen za určitých stavů vybrané entity. Platí společně pro vybrané skupiny ovladačů na tomto Bridge, nikoli jen pro jeden Motion nebo časový blok.

1. Zapněte **Blokovat chování entitou**.
2. Zvolte skupiny, které mají podmínku respektovat: Motion, Button, Dial, Dimmer. Dial zahrnuje kolečko i jeho tlačítka.
3. Vyberte **Řídicí entitu**.
4. Do **Povolené stavy** napište přesné stavy entity, více hodnot oddělte čárkou.

Příklad: entita `sensor.rezim_domacnosti`, povolený stav `doma`, blokovaný pouze Motion. Pohyb rozsvěcí jen při stavu `doma`; ruční ovladače dál fungují. Pokud senzor používá místo toho stav `home`, zadejte `home`. Rozhoduje skutečný stav v **Vývojářské nástroje → Stavy**, včetně velikosti písmen, nikoli přeložený popisek.

Jiný stav, `unknown`, `unavailable` nebo chybějící entita vybrané ovládání zablokují. Návrat do povoleného stavu sám nic nerozsvítí; čeká se na další vstup. Rozběhnutá regulace držením se zastaví. Běžící cykly Motionu mohou doběhnout a zhasnout, ale blokovaný pohyb je neprodlouží ani neobnoví jas při závěrečném ztlumení. Senzory v oficiální integraci dál hlásí své stavy.

Podmínka omezuje akce integrace. Nenahrazuje zabezpečovací systém.

## Spolupráce s Adaptive Lighting

Pokud používáte Adaptive Lighting (AL), můžete zapnout spolupráci. Integrace vyhledá odpovídající konfigurace AL a při ruční regulaci jasu či barvy oznámí ruční řízení službou `adaptive_lighting.set_manual_control`.

- Ruční příznak patří do AL, nikoli do žárovky nebo Hue Bridge.
- Skupiny se rozbalí na známé členy. Označí se jen ovládaná světla, která příslušná konfigurace AL spravuje; při více konfiguracích se osloví každá odpovídající.
- Pokud AL spravuje celou nerozbalenou skupinu, nelze bezpečně označit jen její část. Taková částečná operace se přeskočí s upozorněním v logu. Ovládejte celou skupinu, nebo v AL použijte `expand_light_groups`.
- Ručně nastavený jas a barva jsou rozlišované podle možností nainstalované verze AL. Starší AL může pozastavit i další složku.
- Vlastní jas/barva při zapnutí Motionem se považují za ručně zadané parametry. Jeho dočasné závěrečné ztlumení používá samostatné pozastavení, které se zase uvolní. Obnova jasu před ztlumením sama nevyžaduje nový ruční příznak.

Integrace nemění konfiguraci AL ani nevytváří profily. Obnovení adaptace po ručním zásahu se řídí AL. Bez AL integrace normálně funguje. Ani přímé vypnutí světla nezabrání jiné automatizaci v jeho pozdějším rozsvícení.

## Režim pollingu

| Volba | Co dělá | Kdy ji zvolit |
| --- | --- | --- |
| **Po první události** | Po události spustí dočasné čtení Bridge pro ovladače. V klidu opakované REST čtení neběží. | Doporučený úspornější začátek. |
| **Trvale** | Čte tlačítka a kolečka i v klidu. | Pokud máte důvod testovat trvalé čtení a přijmete vyšší provoz. |

První režim využívá události oficiální integrace a vlastní stream událostí tlačítek z Bridge. Polling potom pomáhá sledovat další aktivitu. Čtení koleček a tlačítek má samostatná aktivní okna; nastavení režimu a intervalu je společné.

Výchozí interval je **0,1 s**, aktivní okno **3 s**. Zadávací pole pro interval a okno se zobrazují při volbě Trvale; přepínání režimů uložené hodnoty zachovává. Okno slouží pro dočasnou aktivitu, trvalý režim čte i mimo něj.

Požadavky jsou hromadné pro celý Bridge, nikoli pro každý ovladač zvlášť. Trvalé čtení při 0,1 s odpovídá přibližně **20 REST požadavkům za sekundu na Bridge** plus stream událostí. Kratší interval zvýší síťový provoz a zátěž HA i Bridge. Požadavky se nepřekrývají a při chybách se čtení zpomaluje. Jde o experimentální nastavení, nikoli doporučení výrobce.

Motion používá změny stavů oficiálních senzorů, nikoli tento rychlý polling. Změna režimu tedy není způsob zrychlení detekce pohybu.

## Když něco nefunguje

| Projev | Co ověřit |
| --- | --- |
| Chybí panel nebo nové prvky | Restart HA po instalaci, obnovení stránky, účet správce. |
| Ovladač je v seznamu, ale nic nedělá | Zapnout ovládání, cíle, konkrétní stisk a společnou podmínku entity. |
| Světlo přeskakuje mezi barvami nebo se samo upravuje | Souběžné přiřazení v Hue, další automatizace a AL. |
| Formulář hlásí „Invalid flow specified“ | Zavřít dialog, obnovit stránku a otevřít čerstvé nastavení. Pokud se opakuje, zkontrolovat log HA. |

Při hlášení chyby uveďte verzi HA a integrace, typ ovladače, nastavenou akci, cílový typ entity a kroky k zopakování. Nezveřejňujte aplikační klíč Bridge ani přístupové tokeny.
