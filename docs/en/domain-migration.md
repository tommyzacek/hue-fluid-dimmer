# Technical domain migration

New installations use only `custom_components/hue_reconfigo`. The old directory is not installed. The panel path is `/hue-reconfigo`, the rotation event is `hue_reconfigo_event`, and the overview WebSocket command is `hue_reconfigo/overview`.

Existing `hue_fluid_dimmer` installations need both a file move and conversion of stored configuration, registries, brightness memories and HACS metadata. Bridge IDs, controller IDs and settings are preserved. Update any user automations listening for the old event and custom panel links separately.

Create a Home Assistant backup first. Obtain the new `custom_components/hue_reconfigo` directory and `tools/migrate_domain.py` from the same repository revision. Do not delete the integration in HA: that deletes its settings.

1. Stop Home Assistant Core (`ha core stop` on HAOS); keep the SSH app available.
2. Copy the new directory to `/config/custom_components/hue_reconfigo`.
3. Preview: `python3 migrate_domain.py --config /config`.
4. Apply: `python3 migrate_domain.py --config /config --apply --core-stopped`.
5. Start Core (`ha core start`) and verify controllers and settings.

The tool validates inputs before writing, rejects conflicting old/new entries, backs up affected existing files privately, and moves the old component into that backup outside `custom_components`. A write exception restores the original files. The printed backup path contains private configuration: do not publish it. `--core-stopped` confirms that you have actually stopped Core; the tool does not stop it.

For rollback, stop Core, restore backed-up storage files into `.storage`, move the old component back, remove the newly created `hue_reconfigo.*.levels` and `hue_reconfigo.*.motion_levels` files, and move the new component outside `custom_components`. Restart Core. Old brightness storage files are retained during migration.
