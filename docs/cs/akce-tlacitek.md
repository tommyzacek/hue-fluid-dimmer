# Společné akce tlačítek

[Čeština](../cs/akce-tlacitek.md) | [Slovenština](../sk/akce-tlacitek.md) | [English](../en/akce-tlacitek.md)

[Všechny návody](README.md) · [Button](button.md) · [Dimmer](dimmer.md) · [Dial](dial.md)

Krátký stisk, dlouhý stisk, dvojklik a trojklik mají vlastní přepínače a nastavení. Nabídka akcí závisí na typu ovladače, stisku a zvolených cílech. Vypnutý stisk neprovádí akci.

## Akce pro světla

| Akce | Výsledek |
| --- | --- |
| **Zapnutí / vypnutí** | Pokud některé z vybraných světel svítí, výběr vypne. Jinak jej zapne podle nastaveného jasu a barvy. |
| **Pouze zapnout** | Vždy provede zapnutí a použije nastavený jas/barvu i u již rozsvíceného světla. Dalším stejným stiskem nevypne. |
| **Pouze vypnout** | Vždy vypne. Nastavení jasu a barvy se pro tuto akci nepoužívá. |
| **Plynulá regulace** | Jen dlouhý stisk: reguluje po dobu držení, puštění ji zastaví. |

Příklad dvou barev: krátký stisk **Zapnutí / vypnutí**, jas 70 %, bílá 4000 K; dvojklik **Pouze zapnout**, jas 30 %, bílá 2300 K. Dvojklik tak přepne vzhled svítícího světla. Kdyby i dvojklik používal Zapnutí / vypnutí, rozsvícené světlo by vypnul.

### Jas a barva jsou nezávislé

| Pole | Volba | Význam |
| --- | --- | --- |
| Jas | **Předchozí stav** | Použije uložený jas. Po závěrečném ztlumení Motionu obnoví jas před ztlumením. Bez uložené hodnoty jas neposílá a ponechá zapnutí na světle či jeho integraci. |
| Jas | **Nastavené %** | Při zapnutí pošle zadaný jas. |
| Barva světla | **Ponechat beze změny** | Nepošle barvu ani teplotu bílé. |
| Barva světla | **Teplota bílé** | Pošle teplotu v kelvinech, omezenou možnostmi daného světla. Posuvník vybírá po stovkách kelvinů. |
| Barva světla | **Vlastní barva** | Pošle zvolenou barvu podporovaným světlům. |

Předchozí stav neznamená obnovení celé scény ani barvy. Integrace si pamatuje jas při vlastním vypnutí a před vlastním závěrečným ztlumením. Není to univerzální historie všech změn ve všech aplikacích. Nepodporovaná barva se světlu neposílá.

Se zapnutou [spoluprací s AL](bridge.md#spolupráce-s-adaptive-lighting) se explicitně zadaný jas a barva označují jako ruční parametry. Ponechání barvy bez změny samo neurčuje, zda ji AL následně upraví.

## Cíle akce

Button a Dimmer mají nahoře **Výchozí světla / zařízení**. Stisk je použije automaticky. Pro výjimku zapněte **Použít pro tuto akci jiná než výchozí zařízení** a vyberte vlastní cíle. Vypnutí této výjimky vrátí akci k výchozímu výběru a zahodí původní vlastní výběr.

Tap Dial má cíle přímo u jednotlivých stisků. Převzetí kolečka používá výběr konkrétního stisku, kterým se vyvolalo.

Lze ovládat světla a jejich skupiny, ventilátory `fan`, číselné entity `number`, nebo jeden skript. Scény ani cyklování scén nejsou přímou součástí nabídky; vlastní posloupnost lze řešit skriptem. Pro běžnou akci nemíchejte různé domény entit v jednom výběru. Regulace potřebuje cíle s ovladatelnou procentní hodnotou.

## Ventilátory a číselné entity

Pro tyto cíle zůstávají dostupné procentní varianty přepínání:

| Volba | Při zapnutí |
| --- | --- |
| Zapnutí / vypnutí | Ventilátor používá své běžné zapnutí; číselný cíl přejde na horní hranici. |
| Vypnuto / předchozí procento | Vrátí nenulovou hodnotu uloženou při vypnutí integrací. Bez uložené hodnoty se ventilátor běžně zapne; u číselného cíle se neodhaduje výkon a zapíše se upozornění do logu. |
| Vypnuto / nastavené procento | Nastaví zadané procento. |
| Pouze zapnout | Nastaví zadané procento i při běžícím zařízení. |
| Pouze vypnout | Nastaví nulu procent rozsahu. |

U `number` se 0–100 % přepočítává na jeho rozsah `min`–`max` a respektuje se `step`. **0 % tedy znamená minimum entity, které nemusí být fyzické vypnutí.** Pro PWM ventilátor ověřte, že jeho minimum skutečně znamená zastavení. Skutečný počet rychlostí ventilátoru může být menší než sto.

## Dlouhé držení

Akce **Plynulá regulace** začne při rozpoznání dlouhého stisku. Uvolnění regulaci zastaví. Směr se vybere na začátku držení:

- pod 30 % nahoru;
- nad 60 % dolů;
- mezi těmito hodnotami opačně než předchozí držení; první držení nahoru.

Po dosažení krajní hodnoty regulace čeká na puštění, během jednoho držení se sama neobrací. Tlačítka + a − Dimmeru mají při regulaci pevný směr. Hue světla mohou využít přímé relativní stmívání se stop příkazem; ostatní zařízení používají služby HA. Viditelný doběh závisí i na zařízení a spojení.

## Dvojklik a trojklik

Pokud nejsou aktivní vícekliky, krátký stisk se vyhodnotí při puštění bez čekání na další klik. Po jejich zapnutí musí integrace čekat, zda přijde pokračování. Rozlišování používá interval **350 ms** a časové značky Bridge; přenos událostí může přidat zpoždění. Dvojklik dělejte přirozeně rychle, není nutné odměřovat přesnou mezeru.

## Skripty

Vyberte jednu entitu `script`. Běžná akce ji spustí přes `script.turn_on`; další stisk ji automaticky nepřepíná do vypnutí jako světlo. Opakované spuštění se řídí režimem skriptu (`single`, `restart`, `queued`, `parallel`). **Pouze vypnout** volá `script.turn_off` a může přerušit i čekající kroky. U skriptů ovládajících zámek nebo jinou důležitou akci s tím počítejte. Pro samotné spouštění je srozumitelná volba Pouze zapnout.
