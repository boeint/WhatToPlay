"""Franchises: create, read, rename, delete, and their rules."""
from conftest import detail


def test_create_trims_the_name_and_adds_at_the_end(client, make_franchise):
    make_franchise("First")
    response = client.post("/api/franchises", json={"name": "  Second  "})
    assert response.status_code == 201
    assert response.json()["name"] == "Second"
    assert [f["name"] for f in client.get("/api/franchises").json()] == ["First", "Second"]


def test_create_with_games_in_one_go(client):
    response = client.post("/api/franchises", json={
        "name": "Series", "games": [{"title": "One"}, {"title": "Two", "status": "finished"}]})
    assert response.status_code == 201
    games = response.json()["games"]
    assert [g["title"] for g in games] == ["One", "Two"]
    assert games[1]["finished_on"] is not None          # finished without a date: today


def test_one_invalid_game_creates_nothing(client):
    response = client.post("/api/franchises", json={
        "name": "Half Valid", "games": [{"title": "Fine"}, {"title": "Bad", "release_month": 5}]})
    assert response.status_code == 422
    assert client.get("/api/franchises").json() == []


def test_names_are_unique_ignoring_case(client, make_franchise):
    make_franchise("BioShock")
    response = client.post("/api/franchises", json={"name": "bioshock"})
    assert response.status_code == 409
    assert "already exists" in detail(response)


def test_names_are_unique_ignoring_accents(client, make_franchise):
    make_franchise("Pokémon")
    assert client.post("/api/franchises", json={"name": "Pokemon"}).status_code == 409


def test_empty_or_missing_name_is_refused(client):
    assert client.post("/api/franchises", json={"name": "   "}).status_code == 422
    assert client.post("/api/franchises", json={"notes": "no name"}).status_code == 422


def test_unknown_fields_are_refused(client):
    response = client.post("/api/franchises", json={"name": "X", "colour": "blue"})
    assert response.status_code == 422


def test_rename_changes_only_what_is_sent(client, make_franchise):
    f = make_franchise("Old", notes="keep me")
    response = client.patch(f"/api/franchises/{f['id']}", json={"name": "New"})
    assert response.status_code == 200
    assert response.json()["name"] == "New"
    assert response.json()["notes"] == "keep me"


def test_rename_to_an_existing_name_is_refused(client, make_franchise):
    make_franchise("Taken")
    f = make_franchise("Mine")
    assert client.patch(f"/api/franchises/{f['id']}", json={"name": "TAKEN"}).status_code == 409


def test_name_cannot_be_set_to_null(client, make_franchise):
    f = make_franchise("Mine")
    assert client.patch(f"/api/franchises/{f['id']}", json={"name": None}).status_code == 422


def test_missing_franchise_is_404(client):
    assert client.get("/api/franchises/999999").status_code == 404
    assert client.patch("/api/franchises/999999", json={"notes": "x"}).status_code == 404
    assert client.delete("/api/franchises/999999").status_code == 404


def test_delete_removes_its_games_too(client, make_franchise):
    f = make_franchise("Gone", [{"title": "A", "platforms": ["PC"]}, {"title": "B"}])
    game_id = f["games"][0]["id"]
    assert client.delete(f"/api/franchises/{f['id']}").status_code == 204
    assert client.get(f"/api/franchises/{f['id']}").status_code == 404
    assert client.get(f"/api/games/{game_id}").status_code == 404
