"""Games: validation, release dates, platforms / play on, the finished date, moving, deleting."""
from datetime import date

import pytest

from conftest import detail


@pytest.fixture
def franchise(make_franchise):
    return make_franchise("Series")


def add(client, franchise, **fields):
    return client.post(f"/api/franchises/{franchise['id']}/games", json={"title": "Game", **fields})


def test_minimal_game_has_sensible_defaults(client, franchise):
    game = add(client, franchise, title="Plain").json()
    assert game["status"] == "unplayed"
    assert game["released"] == ""
    assert game["platforms"] == [] and game["play_on"] is None
    assert game["backloggd_link"] == "https://backloggd.com/games/plain/"


@pytest.mark.parametrize("fields, label", [
    ({"release_year": 2007, "release_month": 8}, "Aug 2007"),
    ({"release_year": 1998}, "1998"),
    ({"release_year": 2026, "release_tba": True}, "2026 (TBA)"),
    ({"release_tba": True}, "TBA"),
])
def test_release_label(client, franchise, fields, label):
    assert add(client, franchise, **fields).json()["released"] == label


@pytest.mark.parametrize("fields, message", [
    ({"release_month": 5}, "release_month needs a release_year"),
    ({"release_year": 2000, "release_month": 13}, "less than or equal to 12"),
    ({"release_year": 1900}, "greater than or equal to 1950"),
    ({"platforms": ["PC", "PS6"]}, "Unknown platform: PS6"),
    ({"platforms": ["PC", "pc"]}, "listed twice"),
    ({"platforms": ["PC"], "play_on": "PS5"}, "play_on must be one of the game's platforms"),
    ({"finished_on": "2024-01-01"}, "finished_on can only be set on a finished game"),
    ({"links": [{"label": "x", "url": "ftp://example.com"}]}, "must start with http"),
    ({"backloggd_url": "backloggd.com/games/x"}, "must start with http"),
    ({"title": "  "}, "at least 1 character"),
    ({"relase_year": 2000}, "Extra inputs are not permitted"),
])
def test_invalid_games_are_refused(client, franchise, fields, message):
    response = add(client, franchise, **fields)
    assert response.status_code == 422
    assert message in detail(response)


def test_platform_names_ignore_case_and_keep_the_given_order(client, franchise):
    game = add(client, franchise, platforms=["ps4", "PC"], play_on="pc").json()
    assert game["platforms"] == ["PS4", "PC"]
    assert game["play_on"] == "PC"


def test_finished_date_rules(client, franchise):
    game = add(client, franchise).json()
    patch = lambda **c: client.patch(f"/api/games/{game['id']}", json=c).json()

    assert patch(status="finished")["finished_on"] == date.today().isoformat()   # becomes finished: today
    assert patch(finished_on="2023-12-25")["finished_on"] == "2023-12-25"         # editable
    assert patch(notes="great")["finished_on"] == "2023-12-25"                    # other edits keep it
    assert patch(status="playing")["finished_on"] is None                         # leaves finished: cleared
    assert patch(status="finished", finished_on="2022-06-01")["finished_on"] == "2022-06-01"


def test_finished_without_date_stays_empty_when_editing_other_fields(client, franchise):
    """Imported finished games have no date; editing them must not stamp today."""
    game = add(client, franchise, status="finished", finished_on=None).json()
    assert game["finished_on"] is None
    assert client.patch(f"/api/games/{game['id']}", json={"notes": "x"}).json()["finished_on"] is None


def test_play_on_is_cleared_when_its_platform_is_removed(client, franchise):
    game = add(client, franchise, platforms=["PC", "PS4"], play_on="PS4").json()
    updated = client.patch(f"/api/games/{game['id']}", json={"platforms": ["PC"]}).json()
    assert updated["play_on"] is None


def test_backloggd_override_and_reset(client, franchise):
    game = add(client, franchise, title="Alan Wake's American Nightmare").json()
    assert game["backloggd_link"].endswith("/alan-wakes-american-nightmare/")
    url = "https://backloggd.com/games/alan-wake-s-american-nightmare/"
    assert client.patch(f"/api/games/{game['id']}", json={"backloggd_url": url}).json()["backloggd_link"] == url
    reset = client.patch(f"/api/games/{game['id']}", json={"backloggd_url": ""}).json()
    assert reset["backloggd_url"] is None and reset["backloggd_link"].endswith("/alan-wakes-american-nightmare/")


def test_links_replace_the_whole_list(client, franchise):
    game = add(client, franchise, links=[{"label": "a", "url": "https://a.example"}]).json()
    updated = client.patch(f"/api/games/{game['id']}", json={"links": [
        {"label": "b", "url": "https://b.example"}, {"label": "c", "url": "https://c.example"}]}).json()
    assert [l["label"] for l in updated["links"]] == ["b", "c"]


def test_move_to_another_franchise_goes_to_its_end(client, make_franchise):
    a = make_franchise("A", [{"title": "Mover"}])
    b = make_franchise("B", [{"title": "Already here"}])
    moved = client.patch(f"/api/games/{a['games'][0]['id']}", json={"franchise_id": b["id"]})
    assert moved.status_code == 200
    assert [g["title"] for g in client.get(f"/api/franchises/{b['id']}").json()["games"]] == ["Already here", "Mover"]
    assert client.get(f"/api/franchises/{a['id']}").json()["games"] == []


def test_move_to_a_missing_franchise_is_refused(client, franchise):
    game = add(client, franchise).json()
    assert client.patch(f"/api/games/{game['id']}", json={"franchise_id": 999999}).status_code == 422


def test_delete_game(client, franchise):
    game = add(client, franchise).json()
    assert client.delete(f"/api/games/{game['id']}").status_code == 204
    assert client.get(f"/api/games/{game['id']}").status_code == 404


def test_length_hours(client, franchise):
    game = add(client, franchise, length_hours=12).json()
    assert game["length_hours"] == 12
    assert client.patch(f"/api/games/{game['id']}", json={"length_hours": 40}).json()["length_hours"] == 40
    assert client.patch(f"/api/games/{game['id']}", json={"length_hours": None}).json()["length_hours"] is None


def test_length_hours_must_be_1_to_999(client, franchise):
    assert add(client, franchise, length_hours=0).status_code == 422
    assert add(client, franchise, length_hours=1000).status_code == 422
