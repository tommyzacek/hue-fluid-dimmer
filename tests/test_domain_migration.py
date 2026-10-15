"""Offline domain conversion preserves IDs, controller settings and unrelated integrations."""

import json

import pytest

from tools.migrate_domain import NEW, OLD, migrate, prepare


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def config(tmp_path):
    storage = tmp_path / ".storage"
    entries = [
        dict(
            domain=OLD,
            entry_id="bridge-a",
            title="Hue Fluid Dimmer – Kitchen",
            data={"hue_entry_id": "official-hue"},
            options={"gate_motion": True},
            subentries=[{"subentry_id": "button-a", "data": {"enabled": True}}],
        ),
        dict(domain="hue", entry_id="official-hue", title="Hue", data={}, options={}),
    ]
    write(storage / "core.config_entries", {"data": {"entries": entries}})
    write(
        storage / "core.device_registry",
        {
            "data": {
                "devices": [
                    {"config_entries": ["bridge-a"], "identifiers": [[OLD, "a"]]},
                    {"config_entries": ["official-hue"], "identifiers": [["hue", "a"]]},
                ]
            }
        },
    )
    write(
        storage / "core.entity_registry",
        {
            "data": {
                "entities": [
                    {
                        "config_entry_id": "official-hue",
                        "platform": "hue",
                        "entity_id": "light.kitchen",
                    }
                ]
            }
        },
    )
    write(
        storage / f"{OLD}.bridge-a.motion_levels",
        {"key": f"{OLD}.bridge-a.motion_levels", "data": {"light.kitchen": 180}},
    )
    write(
        storage / "hacs.repositories",
        {"data": {"1417819497": {"full_name": "tommyzacek/hue-fluid-dimmer", "domain": OLD}}},
    )
    write(tmp_path / "custom_components" / NEW / "manifest.json", {"domain": NEW})
    write(tmp_path / "custom_components" / OLD / "manifest.json", {"domain": OLD})
    return tmp_path


def test_preview_is_read_only(config):
    before = {p: p.read_bytes() for p in config.rglob("*") if p.is_file()}
    count, backup = migrate(config)
    assert count == 4 and backup is None
    assert before == {p: p.read_bytes() for p in config.rglob("*") if p.is_file()}


def test_apply_preserves_ids_settings_and_brightness(config):
    original = json.loads((config / ".storage/core.config_entries").read_text())
    count, backup = migrate(config, apply=True, core_stopped=True)
    result = json.loads((config / ".storage/core.config_entries").read_text())
    assert count == 4
    expected = original["data"]["entries"][0]
    expected.update(domain=NEW, title="Hue Reconfigo – Kitchen")
    assert result == original
    assert json.loads((config / f".storage/{NEW}.bridge-a.motion_levels").read_text())["data"] == {
        "light.kitchen": 180
    }
    assert not (config / "custom_components" / OLD).exists()
    assert (backup / OLD / "manifest.json").exists()
    assert (
        json.loads((backup / "core.config_entries").read_text())["data"]["entries"][0]["domain"]
        == OLD
    )
    assert prepare(config) == {}


def test_apply_requires_stopped_core_confirmation(config):
    with pytest.raises(ValueError, match="Stop Home Assistant"):
        migrate(config, apply=True)
    assert (
        json.loads((config / ".storage/core.config_entries").read_text())["data"]["entries"][0][
            "domain"
        ]
        == OLD
    )


def test_conflicting_brightness_aborts_before_any_write(config):
    write(config / f".storage/{NEW}.bridge-a.motion_levels", {"data": {}})
    with pytest.raises(ValueError, match="already exists"):
        migrate(config, apply=True, core_stopped=True)
    assert (
        json.loads((config / ".storage/core.config_entries").read_text())["data"]["entries"][0][
            "domain"
        ]
        == OLD
    )


def test_duplicate_domain_aborts(config):
    path = config / ".storage/core.config_entries"
    value = json.loads(path.read_text())
    value["data"]["entries"].append(dict(domain=NEW, entry_id="duplicate"))
    write(path, value)
    with pytest.raises(ValueError, match="Both domains"):
        prepare(config)


def test_write_failure_restores_original_files(config, monkeypatch):
    from tools import migrate_domain

    before = {p: p.read_bytes() for p in (config / ".storage").iterdir()}
    real_write = migrate_domain.atomic_write
    calls = 0

    def fail_once(path, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk write failed")
        real_write(path, content)

    monkeypatch.setattr(migrate_domain, "atomic_write", fail_once)
    with pytest.raises(OSError, match="disk write failed"):
        migrate(config, apply=True, core_stopped=True)
    assert before == {p: p.read_bytes() for p in (config / ".storage").iterdir()}
    assert (config / "custom_components" / OLD).exists()
