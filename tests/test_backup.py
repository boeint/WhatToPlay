"""Export, import, the daily backups and restoring them."""
import json

import pytest

from app import backups
from app.config import get_settings
from conftest import detail


def export(client):
    data = client.get("/api/export").json()
    data.pop("exported_at")
    return data


@pytest.fixture
def sample(make_franchise):
    make_franchise("Pokémon", [
        {"title": "Red / Blue", "release_year": 1996, "release_month": 2, "platforms": ["Game Boy"],
         "play_on": "Game Boy", "status": "finished", "finished_on": "2020-05-01", "notes": "first one", "length_hours": 26},
        {"title": "Legends", "release_tba": True, "links": [{"label": "site", "url": "https://example.com"}]},
    ], notes="Mainline only")
    make_franchise("BioShock", [{"title": "BioShock", "backloggd_url": "https://backloggd.com/games/bioshock/"}])


def test_export_is_a_versioned_file_without_ids(client, sample):
    response = client.get("/api/export")
    assert response.headers["content-disposition"].startswith('attachment; filename="whattoplay-export-')
    data = response.json()
    assert data["format"] == "whattoplay-export" and data["version"] == 1
    assert "id" not in data["franchises"][0] and "id" not in data["franchises"][0]["games"][0]


def test_export_import_round_trip_is_identical(client, sample):
    before = export(client)
    assert client.post("/api/import?replace=true", json=client.get("/api/export").json()).status_code == 200
    assert export(client) == before


def test_import_needs_the_safety_latch(client, sample):
    response = client.post("/api/import", json=client.get("/api/export").json())
    assert response.status_code == 422 and "replace=true" in detail(response)


@pytest.mark.parametrize("break_it", [
    lambda d: d.update(format="something-else"),
    lambda d: d["franchises"][0]["games"][0].update(release_year=None),       # month without year
    lambda d: d["franchises"][0]["games"][0]["platforms"].append("PS6"),      # unknown platform
    lambda d: d["franchises"].append({"name": "Pokemon"}),                    # same name, no accent
    lambda d: d["franchises"][0]["games"][0].update(release_note="TBA"),     # old field
])
def test_bad_imports_change_nothing(client, sample, break_it):
    before = export(client)
    data = client.get("/api/export").json()
    break_it(data)
    assert client.post("/api/import?replace=true", json=data).status_code == 422
    assert export(client) == before


def test_import_is_all_or_nothing_inside_the_database(client, sample):
    """A name the database rejects (an invisible character makes it 'equal' to another)
    fails after the old data was deleted: the transaction must roll everything back."""
    before = export(client)
    data = client.get("/api/export").json()
    data["franchises"].append({"name": "BioShock​"})
    assert client.post("/api/import?replace=true", json=data).status_code == 409
    assert export(client) == before


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    """Turn daily backups on, into a temporary folder."""
    monkeypatch.setattr(get_settings(), "backup_dir", str(tmp_path))
    monkeypatch.setattr(get_settings(), "backup_keep", 3)
    return tmp_path


def test_backups_off_without_a_folder(client):
    status = client.get("/api/backups").json()
    assert status["enabled"] is False and "no folder" in status["reason"]


def test_daily_backup_is_written_and_old_ones_pruned(client, sample, backup_dir):
    for day in ("2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"):
        (backup_dir / f"whattoplay-export-{day}.json").write_text("{}")
    (backup_dir / "notes.txt").write_text("not a backup")
    written = backups.write_backup(backup_dir)
    remaining = sorted(p.name for p in backup_dir.iterdir())
    assert written.name in remaining
    assert len([n for n in remaining if n.startswith("whattoplay-export-")]) == 3     # newest 3 kept
    assert "whattoplay-export-2026-01-01.json" not in remaining
    assert "notes.txt" in remaining                                                 # other files untouched
    assert json.loads(written.read_text(encoding="utf-8"))["format"] == "whattoplay-export"


def test_restore_saves_the_current_data_first(client, sample, backup_dir):
    good = backups.write_backup(backup_dir)
    before = export(client)
    client.post("/api/franchises", json={"name": "Added after the backup"})

    response = client.post(f"/api/backups/{good.name}/restore?replace=true")
    assert response.status_code == 200
    assert export(client) == before                                                   # back to the backup
    safety = response.json()["previous_data_saved_as"]
    assert (backup_dir / safety).exists()
    names = [f["name"] for f in json.loads((backup_dir / safety).read_text(encoding="utf-8"))["franchises"]]
    assert "Added after the backup" in names                                          # the undo copy

    listed = client.get("/api/backups").json()
    assert {f["name"]: f["kind"] for f in listed["files"]}[safety] == "before-restore"


@pytest.mark.parametrize("name, status", [
    ("whattoplay-export-2026-01-01.json", 404),       # doesn't exist
    ("..%2F..%2Fsecret.json", 404),                    # not a backup name
    ("broken", 404),
])
def test_restore_refuses_unknown_names(client, backup_dir, name, status):
    assert client.post(f"/api/backups/{name}/restore?replace=true").status_code in (status, 405)


def test_restore_refuses_a_broken_backup_without_touching_anything(client, sample, backup_dir):
    (backup_dir / "whattoplay-export-2026-01-01.json").write_text("{}")
    before = export(client)
    response = client.post("/api/backups/whattoplay-export-2026-01-01.json/restore?replace=true")
    assert response.status_code == 422 and "not a valid backup" in detail(response)
    assert export(client) == before
    assert not list(backup_dir.glob("whattoplay-before-restore-*"))                   # no safety copy made
