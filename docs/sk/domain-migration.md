# Prevod technickej domény

Nové inštalácie používajú iba `custom_components/hue_reconfigo`. Panel je na `/hue-reconfigo`, udalosť rotácie je `hue_reconfigo_event` a príkaz WebSocket API je `hue_reconfigo/overview`.

Pri existujúcich inštaláciách treba previesť aj uloženú konfiguráciu, registre, pamäť jasu a metadáta HACS. ID Bridge, ovládačov a ich nastavenia zostanú zachované. Vlastné automatizácie sledujúce starú udalosť a odkazy treba upraviť samostatne. Integráciu v HA neodstraňujte.

Najskôr vytvorte zálohu HA. Z rovnakej verzie repozitára získajte nový priečinok komponentu a nástroj `tools/migrate_domain.py`.

1. Zastavte Core (`ha core stop` na HAOS). SSH doplnok musí zostať dostupný.
2. Nový priečinok umiestnite do `/config/custom_components/hue_reconfigo`.
3. Spustite kontrolu: `python3 migrate_domain.py --config /config`.
4. Vykonajte prevod: `python3 migrate_domain.py --config /config --apply --core-stopped`.
5. Spustite Core (`ha core start`) a overte ovládače aj nastavenia.

Nástroj overí vstupy, odmietne súbežné konfigurácie oboch domén a vytvorí súkromnú zálohu menených súborov. Starý priečinok presunie do zálohy mimo `custom_components`. Pri chybe zápisu obnoví pôvodné súbory. Zálohu nepublikujte: obsahuje súkromné údaje. `--core-stopped` potvrdzuje, že ste Core skutočne zastavili; nástroj ho sám nezastavuje.

Pri návrate zastavte Core, obnovte zálohované súbory do `.storage`, presuňte starý priečinok späť a nový odložte mimo `custom_components`. Odstráňte novo vytvorené súbory `hue_reconfigo.*.levels` a `hue_reconfigo.*.motion_levels` a spustite Core. Staré kópie pamäte jasu zostávajú zachované.
