"""The platform list: usage counts, add, rename, reorder, delete."""
from conftest import detail


def names(client):
    return [p["name"] for p in client.get("/api/platforms").json()]


def test_starts_with_the_31_platforms(client):
    assert len(names(client)) == 31
    assert names(client)[:3] == ["PC", "PS5", "PS4"]


def test_usage_counts(client, make_franchise):
    make_franchise("S", [{"title": "A", "platforms": ["SNES"]}, {"title": "B", "platforms": ["SNES", "PC"]}])
    used = {p["name"]: p["used_by"] for p in client.get("/api/platforms").json()}
    assert used["SNES"] == 2 and used["PC"] == 1 and used["N64"] == 0


def test_add_and_place_after_switch(client):
    created = client.post("/api/platforms", json={"name": " NSO "})
    assert created.status_code == 201 and created.json()["name"] == "NSO"
    ids = {p["name"]: p["id"] for p in client.get("/api/platforms").json()}
    order = [n for n in names(client) if n != "NSO"]
    order.insert(order.index("Switch") + 1, "NSO")
    assert client.put("/api/platform-order", json=[ids[n] for n in order]).status_code == 204
    assert names(client)[names(client).index("Switch") + 1] == "NSO"


def test_duplicate_names_are_refused(client):
    assert client.post("/api/platforms", json={"name": "pc"}).status_code == 409


def test_rename_shows_on_games(client, make_franchise):
    f = make_franchise("S", [{"title": "A", "platforms": ["Genesis"]}])
    genesis = next(p for p in client.get("/api/platforms").json() if p["name"] == "Genesis")
    assert client.patch(f"/api/platforms/{genesis['id']}", json={"name": "Mega Drive"}).status_code == 200
    assert client.get(f"/api/games/{f['games'][0]['id']}").json()["platforms"] == ["Mega Drive"]


def test_used_platform_cannot_be_deleted(client, make_franchise):
    make_franchise("S", [{"title": "A", "platforms": ["SNES"]}])
    snes = next(p for p in client.get("/api/platforms").json() if p["name"] == "SNES")
    response = client.delete(f"/api/platforms/{snes['id']}")
    assert response.status_code == 409
    assert "used by 1 game" in detail(response)


def test_unused_platform_can_be_deleted(client):
    new = client.post("/api/platforms", json={"name": "Temporary"}).json()
    assert client.delete(f"/api/platforms/{new['id']}").status_code == 204
    assert "Temporary" not in names(client)
