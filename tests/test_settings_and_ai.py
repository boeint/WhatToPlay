"""Settings, the health check, and the AI assistant (MCP) with its on/off switch."""
import json
from concurrent.futures import ThreadPoolExecutor

import anyio
from mcp.client import Client

from app.mcp_server import mcp

MCP_REQUEST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
MCP_HEADERS = {"Accept": "application/json, text/event-stream"}


def call_tool(name, arguments):
    """Call one MCP tool in-process, as an assistant would; returns (is_error, text)."""
    async def run():
        async with Client(mcp) as c:
            result = await c.call_tool(name, arguments)
            error = getattr(result, "is_error", None) or getattr(result, "isError", None)
            return bool(error), " ".join(getattr(part, "text", "") for part in result.content)
    # In its own thread: the browser tests (Playwright) keep an event loop running in this one.
    with ThreadPoolExecutor(1) as thread:
        return thread.submit(anyio.run, run).result()


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["backups"]["enabled"] is False


def test_settings_defaults_and_save(client):
    s = client.get("/api/settings").json()
    assert s["ai_enabled"] is False
    assert s["ai_instructions"] == s["default_ai_instructions"]
    saved = client.patch("/api/settings", json={"ai_enabled": True, "ai_instructions": "Mine"}).json()
    assert saved["ai_enabled"] is True and saved["ai_instructions"] == "Mine"
    assert client.patch("/api/settings", json={"ai_enabled": "maybe"}).status_code == 422


def test_mcp_is_refused_while_the_switch_is_off(client):
    response = client.post("/mcp/", json=MCP_REQUEST, headers=MCP_HEADERS)
    assert response.status_code == 403
    assert "turned off" in response.json()["error"]


def test_mcp_answers_when_switched_on(client):
    client.patch("/api/settings", json={"ai_enabled": True})
    response = client.post("/mcp/", json=MCP_REQUEST, headers=MCP_HEADERS)
    assert response.status_code != 403


def test_tools_list_read_and_search(client, make_franchise):
    make_franchise("Metroid", [{"title": "Metroid Prime"}, {"title": "Super Metroid", "status": "finished"}])
    error, text = call_tool("list_franchises", {})
    franchises = json.loads(text)["franchises"]
    assert not error and franchises == [{"name": "Metroid", "games": 2, "done": 1, "next_up": "Metroid Prime"}]
    assert "Metroid Prime" in call_tool("get_franchise", {"name": "metroid"})[1]
    assert json.loads(call_tool("search_games", {"query": "prime"})[1])["matches"][0]["title"] == "Metroid Prime"


def test_instructions_include_the_platform_names(client):
    client.patch("/api/settings", json={"ai_instructions": "My rules"})
    error, text = call_tool("get_instructions", {})
    assert not error and text.startswith("My rules") and "SNES" in text


def test_tools_add_and_update_with_the_app_rules(client):
    error, _ = call_tool("add_franchise", {"name": "Zelda", "games": [
        {"title": "A Link to the Past", "release_year": 1991, "release_month": 11,
         "platforms": ["SNES"], "play_on": "SNES"},
        {"title": "Mobile spin-off", "platforms": ["Mobile"], "status": "skip", "notes": "Mobile-only"}]})
    assert not error
    assert not call_tool("add_games", {"franchise": "zelda", "games": [{"title": "Next", "release_tba": True}]})[0]
    assert not call_tool("update_game", {"franchise": "Zelda", "title": "next",
                                         "changes": {"release_year": 2027, "release_tba": False}})[0]
    games = client.get("/api/franchises").json()[0]["games"]
    assert [(g["title"], g["released"], g["status"]) for g in games] == [
        ("A Link to the Past", "Nov 1991", "unplayed"), ("Mobile spin-off", "", "skip"), ("Next", "2027", "unplayed")]


def test_tools_explain_what_went_wrong(client, make_franchise):
    make_franchise("Taken")
    cases = [
        ("get_franchise", {"name": "Nope"}, "No franchise named 'Nope'"),
        ("add_franchise", {"name": "taken", "games": []}, "already exists"),
        ("add_franchise", {"name": "Bad", "games": [{"title": "x", "release_month": 4}]}, "release_month needs a release_year"),
        ("update_game", {"franchise": "Taken", "title": "Missing", "changes": {}}, "No game titled 'Missing'"),
    ]
    for tool, arguments, message in cases:
        error, text = call_tool(tool, arguments)
        assert error and message in text, (tool, text)
    assert [f["name"] for f in client.get("/api/franchises").json()] == ["Taken"]     # nothing written


def test_list_games_filters(client, make_franchise):
    make_franchise("Series", [
        {"title": "Done", "status": "finished", "length_hours": 10},
        {"title": "No length"},
        {"title": "Coming", "release_tba": True, "length_hours": 30},
    ])
    make_franchise("Other", [{"title": "Elsewhere", "length_hours": 5}])
    listed = lambda **filters: [g["title"] for g in json.loads(call_tool("list_games", filters)[1])["games"]]
    assert sorted(listed()) == ["Coming", "Done", "Elsewhere", "No length"]
    assert listed(missing_length=True) == ["No length"]
    assert listed(tba_only=True) == ["Coming"]
    assert listed(status="finished") == ["Done"]
    assert listed(status="unplayed", missing_length=True) == ["No length"]
    assert listed(franchise="other") == ["Elsewhere"]
    error, text = call_tool("list_games", {"franchise": "Nope"})
    assert error and "No franchise named" in text


def test_update_game_sets_a_length(client, make_franchise):
    make_franchise("Series", [{"title": "Game"}])
    assert not call_tool("update_game", {"franchise": "Series", "title": "Game", "changes": {"length_hours": 18}})[0]
    assert client.get("/api/franchises").json()[0]["games"][0]["length_hours"] == 18
