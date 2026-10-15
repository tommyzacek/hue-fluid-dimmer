"""Offline, backed-up migration to hue_reconfigo. Run only with HA Core stopped."""

import argparse
import json
import os
import shutil
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

OLD = "hue_fluid_dimmer"
NEW = "hue_reconfigo"
REPOSITORY_ID = "1417819497"


def prepare(config: Path) -> dict[Path, bytes]:
    """Validate all inputs and build changes without writing or exposing configuration."""
    storage = config / ".storage"
    entries_path = storage / "core.config_entries"
    entries = json.loads(entries_path.read_text())
    own = [e for e in entries["data"]["entries"] if e["domain"] == OLD]
    if not own:
        return {}
    ids = {e["entry_id"] for e in own}
    existing = [e for e in entries["data"]["entries"] if e["domain"] == NEW]
    if existing:
        raise ValueError("Both domains are configured; resolve duplicate entries before migrating")
    changes = {}

    def stage(path, value):
        changes[path] = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()

    for entry in own:
        entry["domain"] = NEW
        if entry["title"].startswith("Hue Fluid Dimmer – "):
            entry["title"] = entry["title"].replace("Hue Fluid Dimmer – ", "Hue Reconfigo – ", 1)
    stage(entries_path, entries)
    for filename, collection in [
        ("core.entity_registry", "entities"),
        ("core.device_registry", "devices"),
    ]:
        path = storage / filename
        if not path.exists():
            continue
        value = json.loads(path.read_text())
        before = deepcopy(value)
        for row in value["data"][collection]:
            if collection == "entities":
                if row.get("config_entry_id") in ids and row.get("platform") == OLD:
                    row["platform"] = NEW
            elif ids.intersection(row.get("config_entries", [])):
                row["identifiers"] = [
                    [NEW if domain == OLD else domain, key]
                    for domain, key in row.get("identifiers", [])
                ]
        if value != before:
            stage(path, value)
    for entry_id in ids:
        for suffix in ("levels", "motion_levels"):
            source = storage / f"{OLD}.{entry_id}.{suffix}"
            target = storage / f"{NEW}.{entry_id}.{suffix}"
            if source.exists():
                if target.exists():
                    raise ValueError("Target brightness storage already exists; no files changed")
                value = json.loads(source.read_text())
                value["key"] = target.name
                stage(target, value)
    # HACS stores the repository domain in both current and historical storage layouts.
    for path in storage.glob("hacs*"):
        if not path.is_file():
            continue
        value = json.loads(path.read_text())
        before = deepcopy(value)

        def visit(node, key=None):
            if isinstance(node, dict):
                owned = str(node.get("id", key)) == REPOSITORY_ID or node.get("full_name") in (
                    "tommyzacek/hue-fluid-dimmer",
                    "tommyzacek/hue-reconfigo",
                )
                if owned and node.get("domain") == OLD:
                    node["domain"] = NEW
                    if "full_name" in node:
                        node["full_name"] = "tommyzacek/hue-reconfigo"
                for child_key, child in node.items():
                    visit(child, child_key)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(value)
        if value != before:
            stage(path, value)
    return changes


def atomic_write(path: Path, content: bytes):
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def migrate(config: Path, *, apply=False, core_stopped=False):
    changes = prepare(config)
    if not apply or not changes:
        return len(changes), None
    if not core_stopped:
        raise ValueError("Stop Home Assistant Core first, then pass --core-stopped")
    manifest = config / "custom_components" / NEW / "manifest.json"
    if not manifest.exists() or json.loads(manifest.read_text()).get("domain") != NEW:
        raise ValueError("Install the new hue_reconfigo component before applying migration")
    backup = (
        config
        / "backups"
        / ("hue-reconfigo-domain-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    )
    backup.mkdir(parents=True, mode=0o700)
    existing = {path for path in changes if path.exists()}
    for path in existing:
        shutil.copy2(path, backup / path.name)
    old_code = config / "custom_components" / OLD
    moved = False
    try:
        for path, content in changes.items():
            atomic_write(path, content)
        if old_code.exists():
            shutil.move(str(old_code), backup / OLD)
            moved = True
    except BaseException:
        for path in changes:
            if path in existing:
                atomic_write(path, (backup / path.name).read_bytes())
            else:
                path.unlink(missing_ok=True)
        if moved:
            shutil.move(str(backup / OLD), old_code)
        raise
    return len(changes), backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("/config"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--core-stopped", action="store_true", help="Confirm Core was stopped externally"
    )
    args = parser.parse_args()
    count, backup = migrate(args.config, apply=args.apply, core_stopped=args.core_stopped)
    print(f"{'Migrated' if args.apply else 'Planned'} files: {count}")
    if backup:
        print(f"Private backup: {backup}")


if __name__ == "__main__":
    main()
