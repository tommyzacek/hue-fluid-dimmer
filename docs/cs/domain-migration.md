# Převod technické domény

Nové instalace používají pouze `custom_components/hue_reconfigo`. Starý adresář se neinstaluje. Panel je na `/hue-reconfigo`, událost rotace je `hue_reconfigo_event` a WebSocket API používá `hue_reconfigo/overview`.

U instalací s doménou `hue_fluid_dimmer` nestačí přesunout soubory. Uložená konfigurace, registry, paměť jasů i metadata HACS musí používat novou doménu. ID Bridge, ID ovladačů a jejich nastavení se zachovají. Automatizace uživatele poslouchající starý název události a vlastní odkazy je potřeba upravit samostatně.

Před převodem vytvořte zálohu HA. Stáhněte ze stejné verze repozitáře nový adresář `custom_components/hue_reconfigo` a nástroj `tools/migrate_domain.py`. Neodstraňujte integraci v HA, tím by se smazalo její nastavení.

1. Zastavte Home Assistant Core (na HAOS `ha core stop`). SSH doplněk musí zůstat dostupný.
2. Umístěte nový adresář do `/config/custom_components/hue_reconfigo`.
3. Nejdříve spusťte kontrolu: `python3 migrate_domain.py --config /config`.
4. Proveďte převod: `python3 migrate_domain.py --config /config --apply --core-stopped`.
5. Spusťte Core (`ha core start`) a ověřte ovladače i uložené nastavení.

Nástroj nejprve zkontroluje všechny soubory, odmítne souběžnou konfiguraci obou domén a vytvoří soukromou zálohu měněných souborů. Starý adresář přesune do této zálohy mimo `custom_components`. Při chybě zápisu obnoví původní soubory. Cestu zálohy vypíše; obsahuje neveřejná data a nesmí se publikovat. Přepínač `--core-stopped` je potvrzení skutečného zastavení, nástroj sám Core nezastavuje.

Při návratu zastavte Core a obnovte soubory ze zálohy do `.storage`, přesuňte původní adresář zpět a odstraňte nově vytvořené soubory `hue_reconfigo.*.levels` a `hue_reconfigo.*.motion_levels`. Nový adresář komponenty odložte mimo `custom_components`. Poté Core spusťte. Staré kopie paměti jasů zůstávají během převodu zachované.
