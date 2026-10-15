# Bridge a spoločné nastavenia

[Čeština](../cs/bridge.md) | [Slovenčina](../sk/bridge.md) | [English](../en/bridge.md)

[Všetky návody](README.md)

## Inštalácia a otvorenie nastavení

1. V HACS pridajte `https://github.com/tommyzacek/hue-fluid-dimmer` ako vlastný repozitár typu **Integration**.
2. Stiahnite požadované vydanie a reštartujte Home Assistant. Pre predbežné vydania povoľte ich zobrazovanie v HACS.
3. V **Nastavenia → Zariadenia a služby → Pridať integráciu** vyberte Hue Fluid Dimmer a existujúci Hue Bridge.
4. Otvorte bočný panel **Hue Fluid Dimmer**. Ovládače sú rozdelené na Dial, Button, Dimmer a Motion.

Ozubené koliesko vedľa názvu Bridge otvorí spoločné nastavenia priamo v paneli. Dostupné zostávajú aj štandardné nastavenia integrácie v Zariadenia a služby. Panel nevyžaduje samostatnú inštaláciu, nevytvára ďalší Bridge ani duplicitné entity a sám nepridáva pravidelné dopytovanie.

## Blokovať správanie entitou

Táto funkcia vznikla z potreby zabrániť automatickému rozsvieteniu v prázdnej domácnosti. Senzor môže zaznamenať pohyb zvieraťa, nechcený podnet alebo neoprávnený vstup — a vtedy nemusí byť žiaduce rozsvietiť. Ak už máte v HA entitu určujúcu stav domácnosti, môžete na ňu ovládanie naviazať: napríklad povoliť Motion len v stave „doma“ a ručné ovládače ponechať funkčné. Rovnaký princíp podporuje ďalšie vlastné podmienky bez závislosti od konkrétneho systému prítomnosti.

Ovládanie je povolené len v určitých stavoch vybranej entity. Podmienka platí spoločne pre vybrané skupiny ovládačov na tomto Bridge, nielen pre jeden Motion alebo časový blok.

1. Zapnite **Blokovať správanie entitou**.
2. Vyberte skupiny, ktoré majú podmienku rešpektovať: Motion, Button, Dial, Dimmer. Dial zahŕňa koliesko aj jeho tlačidlá.
3. Vyberte **Riadiacu entitu**.
4. Do **Povolené stavy** napíšte presné stavy entity, viaceré hodnoty oddeľte čiarkou.

Príklad: entita `sensor.rezim_domacnosti`, povolený stav `doma`, blokovaný iba Motion. Pohyb rozsvieti len pri stave `doma`; ručné ovládače ďalej fungujú. Ak senzor používa stav `home`, zadajte `home`. Rozhoduje skutočný stav vo **Vývojárske nástroje → Stavy**, vrátane veľkosti písmen, nie preložený popis.

Iný stav, `unknown`, `unavailable` alebo chýbajúca entita vybrané ovládanie zablokujú. Návrat do povoleného stavu sám nič nerozsvieti; čaká sa na ďalší vstup. Prebiehajúca regulácia podržaním sa zastaví. Existujúce cykly Motionu môžu dobehnúť a zhasnúť, blokovaný pohyb ich však nepredĺži ani neobnoví jas pri záverečnom stlmení. Oficiálne senzory ďalej hlásia svoje stavy.

Podmienka obmedzuje akcie integrácie. Nenahrádza zabezpečovací systém.

## Spolupráca s Adaptive Lighting

**Adaptive Lighting (AL) je samostatná, voliteľná vlastná integrácia inštalovaná cez HACS.** Nie je súčasťou oficiálnej integrácie Philips Hue a pre fungovanie Hue Fluid Dimmer nie je potrebná. Oficiálna integrácia Philips Hue je naopak vyžadovaná a musí zostať zapnutá.

Ak používate Adaptive Lighting (AL), môžete zapnúť spoluprácu. Integrácia vyhľadá zodpovedajúce konfigurácie AL a pri ručnej regulácii jasu či farby oznámi ručné ovládanie službou `adaptive_lighting.set_manual_control`.

- Ručný príznak patrí do AL, nie do žiarovky alebo Hue Bridge.
- Skupiny sa rozbalia na známych členov. Označia sa iba ovládané svetlá spravované príslušnou konfiguráciou AL; pri viacerých konfiguráciách sa osloví každá zodpovedajúca.
- Ak AL spravuje celú nerozbalenú skupinu, nemožno bezpečne označiť iba jej časť. Takáto operácia sa preskočí s upozornením v logu. Ovládajte celú skupinu alebo v AL použite `expand_light_groups`.
- Jas a farba sa rozlišujú podľa možností nainštalovanej verzie AL. Staršie AL môže pozastaviť aj druhú zložku.
- Vlastný jas/farba pri zapnutí Motionom sa považujú za ručne zadané parametre. Dočasné záverečné stlmenie používa samostatné pozastavenie, ktoré sa opäť uvoľní. Obnova jasu pred stlmením sama nevyžaduje nový ručný príznak.

Integrácia nemení konfiguráciu AL ani nevytvára profily. Obnovenie adaptácie po ručnom zásahu určuje AL. Bez AL integrácia funguje normálne. Ani priame vypnutie svetla nezabráni inej automatizácii v jeho neskoršom rozsvietení.

## Režim pollingu

| Voľba | Čo robí | Kedy ju zvoliť |
| --- | --- | --- |
| **Po prvej udalosti** | Po udalosti spustí dočasné čítanie Bridge. V pokoji opakované REST čítanie nebeží. | Odporúčaný úspornejší začiatok. |
| **Trvalo** | Číta tlačidlá a kolieska aj v pokoji. | Ak máte dôvod testovať trvalé čítanie a prijmete vyššiu prevádzku. |

Prvý režim využíva udalosti oficiálnej integrácie a vlastný stream udalostí tlačidiel z Bridge. Polling potom pomáha sledovať ďalšiu aktivitu. Kolieska a tlačidlá majú samostatné aktívne okná; režim a interval sú spoločné.

Predvolený interval je **0,1 s**, aktívne okno **3 s**. Polia intervalu a okna sa zobrazujú pri voľbe Trvalo; prepínanie režimov uložené hodnoty zachováva. Okno slúži pre dočasnú aktivitu, trvalý režim číta aj mimo neho.

Požiadavky sú hromadné pre celý Bridge, nie pre každý ovládač zvlášť. Trvalé čítanie pri 0,1 s predstavuje približne **20 REST požiadaviek za sekundu na Bridge** plus stream udalostí. Kratší interval zvýši sieťovú prevádzku a záťaž HA aj Bridge. Požiadavky sa neprekrývajú a pri chybách sa čítanie spomaľuje. Ide o experimentálne nastavenie, nie odporúčanie výrobcu.

Motion používa zmeny stavov oficiálnych senzorov, nie tento rýchly polling. Zmena režimu preto nezrýchľuje detekciu pohybu.

## Keď niečo nefunguje

| Prejav | Čo overiť |
| --- | --- |
| Chýba panel alebo nové prvky | Reštart HA po inštalácii, obnovenie stránky, účet správcu. |
| Ovládač je v zozname, ale nič nerobí | Zapnúť ovládanie, ciele, konkrétne stlačenie a spoločnú podmienku entity. |
| Svetlo mení farby alebo sa samo upravuje | Súbežné priradenie v Hue, ďalšie automatizácie a AL. |
| „Invalid flow specified“ | Zavrieť dialóg, obnoviť stránku a otvoriť nové nastavenie. Ak sa opakuje, skontrolovať log HA. |

Pri hlásení chyby uveďte verziu HA a integrácie, model ovládača, akciu, typ cieľovej entity a postup zopakovania. Nezverejňujte aplikačný kľúč Bridge ani prístupové tokeny.
