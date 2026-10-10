"""Length lookup from HowLongToBeat, with the site replaced by a fake (tests never go online)."""
import json
from types import SimpleNamespace

import pytest

from app import lengths
from tests.test_settings_and_ai import call_tool


def entry(name, year, main_story, players, similarity=1.0, game_id=1):
    return SimpleNamespace(game_name=name, release_world=year, main_story=main_story, similarity=similarity,
                           game_id=game_id, json_content={"comp_main_count": players})


@pytest.fixture
def hltb(monkeypatch):
    """Sets what the fake HowLongToBeat answers; records what was searched."""
    fake = SimpleNamespace(results=[], searched=[])

    class FakeHowLongToBeat:
        async def async_search(self, text):
            fake.searched.append(text)
            if isinstance(fake.results, Exception):
                raise fake.results
            return fake.results

    monkeypatch.setattr(lengths, "HowLongToBeat", FakeHowLongToBeat)
    return fake


def test_best_match_first_with_rounded_hours(client, hltb):
    hltb.results = [
        entry("Crash Bandicoot N. Sane Trilogy", 2017, 14.96, 578, similarity=0.6, game_id=46381),
        entry("Crash Bandicoot", 1996, 6.06, 544, game_id=1),
    ]
    body = client.get("/api/length-lookup", params={"title": "Crash Bandicoot (N. Sane Trilogy)"}).json()
    assert hltb.searched == ["Crash Bandicoot"]               # the edition in brackets is left out
    assert [m["name"] for m in body["matches"]] == ["Crash Bandicoot", "Crash Bandicoot N. Sane Trilogy"]
    assert body["matches"][0] == {"name": "Crash Bandicoot", "year": 1996, "main_story": 6.1, "hours": 6,
                                  "players": 544, "url": "https://howlongtobeat.com/game/1"}


def test_release_year_breaks_ties_and_rounding_is_half_up(client, hltb):
    hltb.results = [entry("Doom", 2016, 11.5, 900), entry("Doom", 1993, 4.5, 600)]
    matches = client.get("/api/length-lookup", params={"title": "Doom", "year": 1993}).json()["matches"]
    assert [(m["year"], m["hours"]) for m in matches] == [(1993, 5), (2016, 12)]


def test_tiny_and_missing_times(client, hltb):
    hltb.results = [entry("Kirby's Dream Land", 1992, 0.78, 931), entry("Unreleased", 2030, 0, 0)]
    matches = client.get("/api/length-lookup", params={"title": "Kirby"}).json()["matches"]
    assert [m["hours"] for m in matches] == [1, None]      # at least 1 hour; no time = no figure


def test_site_unavailable_is_a_clear_error(client, hltb):
    hltb.results = None                                    # the package's "request failed"
    response = client.get("/api/length-lookup", params={"title": "Doom"})
    assert response.status_code == 502 and "HowLongToBeat" in response.json()["detail"]
    hltb.results = RuntimeError("site changed")
    assert client.get("/api/length-lookup", params={"title": "Doom"}).status_code == 502


def test_title_is_required(client, hltb):
    assert client.get("/api/length-lookup").status_code == 422
    assert client.get("/api/length-lookup", params={"title": ""}).status_code == 422


def test_mcp_tool(client, hltb):
    hltb.results = [entry("Portal", 2007, 3.12, 8082)]
    error, text = call_tool("lookup_length", {"title": "Portal", "year": 2007})
    assert not error and json.loads(text)["matches"][0]["hours"] == 3
    hltb.results = None
    error, text = call_tool("lookup_length", {"title": "Portal"})
    assert error and "couldn't be searched" in text
