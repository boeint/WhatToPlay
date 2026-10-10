"""Reordering games within a franchise, and the franchises themselves."""


def titles(client, franchise_id):
    return [g["title"] for g in client.get(f"/api/franchises/{franchise_id}").json()["games"]]


def test_game_order_is_saved(client, make_franchise):
    f = make_franchise("Series", [{"title": "One"}, {"title": "Two"}, {"title": "Three"}])
    ids = [g["id"] for g in f["games"]]
    response = client.put(f"/api/franchises/{f['id']}/game-order", json=[ids[2], ids[0], ids[1]])
    assert response.status_code == 200
    assert titles(client, f["id"]) == ["Three", "One", "Two"]


def test_game_order_must_list_every_game_exactly_once(client, make_franchise):
    f = make_franchise("Series", [{"title": "One"}, {"title": "Two"}])
    other = make_franchise("Other", [{"title": "Elsewhere"}])
    ids = [g["id"] for g in f["games"]]
    url = f"/api/franchises/{f['id']}/game-order"
    assert client.put(url, json=ids[:1]).status_code == 422                          # missing one
    assert client.put(url, json=[ids[0], ids[0]]).status_code == 422                 # twice
    assert client.put(url, json=ids + [other["games"][0]["id"]]).status_code == 422  # from another franchise
    assert titles(client, f["id"]) == ["One", "Two"]                                 # unchanged


def test_franchise_order(client, make_franchise):
    a, b, c = make_franchise("A"), make_franchise("B"), make_franchise("C")
    assert client.put("/api/franchise-order", json=[c["id"], a["id"], b["id"]]).status_code == 204
    assert [f["name"] for f in client.get("/api/franchises").json()] == ["C", "A", "B"]
    assert client.put("/api/franchise-order", json=[a["id"]]).status_code == 422
