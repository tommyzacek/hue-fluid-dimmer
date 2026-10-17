<p align="center">
  <img src="docs/assets/hue-reconfigo-logo.png" alt="Hue Reconfigo" width="360">
</p>

# Hue Reconfigo

[Čeština](README.cs.md) | [Slovenština](README.sk.md) | [English](README.md)

Nastavte **Hue Tap Dial, Smart Button, Dimmer v2 a pohybové senzory** priamo v Home Assistante. Akcie, jas, farbu aj správanie pri pohybe zvolíte vo formulároch, bez YAML a samostatných automatizácií pre každý ovládač. Ovládajte svetlá aj ďalšie kompatibilné zariadenia s dôrazom na rýchlu odozvu a plynulú reguláciu.

<p align="center">
  <img src="docs/assets/screenshots/panel.png" alt="Bočný panel Hue Reconfigo" width="760">
</p>

Vyžaduje **Home Assistant 2026.10.1 alebo novší**, **Hue Bridge s API v2** a nastavenú oficiálnu integráciu **Philips Hue**.

**Adaptive Lighting je voliteľné.** Ak ho používate, zapnite spoluprácu v nastavení Bridge, aby mu Hue Reconfigo oznamoval ručné zmeny jasu a farby. [Podrobnosti prepojenia](docs/sk/bridge.md#spolupráca-s-adaptive-lighting).

## Rýchla inštalácia

[![Otvoriť v HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tommyzacek&repository=hue-reconfigo&category=integration)

1. Do HACS pridajte `https://github.com/tommyzacek/hue-reconfigo` ako vlastný repozitár typu **Integration**.
2. Stiahnite vydanie a reštartujte Home Assistant.
3. V **Nastavenia → Zariadenia a služby** pridajte **Hue Reconfigo** a vyberte existujúci Hue Bridge.
4. V Hue nastavte príslušenstvo na **Konfigurovať v inej aplikácii**. Vypnite konkurenčné automatizácie pre rovnaké vstupy; oficiálnu Hue integráciu ponechajte zapnutú.
5. Ako správca otvorte bočný panel **Hue Reconfigo**. Vyberte ovládač, nastavte ciele/akcie a zapnite ovládanie. Koliesko vedľa Bridge otvorí spoločné nastavenia. Po aktualizáciách obnovte stránku.

Po stiahnutí a reštarte Home Assistanta:

[![Pridať integráciu](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hue_reconfigo)

Ručná inštalácia: skopírujte `custom_components/hue_reconfigo` do priečinka `custom_components` v konfigurácii HA a reštartujte. Bočný panel je súčasťou integrácie.

## Používateľské návody

| Skupina | Návod |
| --- | --- |
| Bridge | [Inštalácia, spoločné podmienky, Adaptive Lighting a polling](docs/sk/bridge.md) |
| Dial | [Predvoľby kolieska, štyri tlačidlá a dočasné prevzatie](docs/sk/dial.md) |
| Button | [Krátke/dlhé stlačenie, dvojklik a trojklik](docs/sk/button.md) |
| Dimmer | [ON/OFF, +, − a HUE na Dimmeri v2](docs/sk/dimmer.md) |
| Motion | [Časové bloky, citlivosť na svetlo, časovač a ručný zásah](docs/sk/motion.md) |
| Spoločné akcie | [Zapnutie, jas, farba, držanie, ventilátory a skripty](docs/sk/akce-tlacitek.md) |

Rozhranie aj návody sú česky, slovensky a anglicky. Nové ovládače začínajú vypnuté. Natívne prechody Hue môžu hlásiť cieľový stav pred dokončením stlmenia; odozva a plynulosť závisia od zariadení a siete.

Nezávislý projekt bez väzby na Signify či Home Assistant. Návody sledujú aktuálny vývoj; rozsah nainštalovanej verzie nájdete v [poznámkach k vydaniu](https://github.com/tommyzacek/hue-reconfigo/releases), obmedzenia v [technických poznámkach](docs/development.md).
