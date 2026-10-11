"""The page itself, in a real browser (Chromium, driven by Playwright).

The other tests call the API; these click through the page like a person would, so
they catch a broken button, a JavaScript error or a layout that spills off a phone.
Each test gets a fresh browser tab and its own small backlog.
"""
import json

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def backlog(make_franchise):
    """Two franchises: Zelda (one game finished, the next one short-listed) and Portal."""
    zelda = make_franchise("Zelda", [
        {"title": "The Legend of Zelda", "status": "finished", "finished_on": "2025-03-02", "length_hours": 8,
         "release_year": 1986, "platforms": ["NES"], "play_on": "NES"},
        {"title": "A Link to the Past", "length_hours": 15, "release_year": 1991, "release_month": 11,
         "platforms": ["SNES"], "play_on": "SNES"},
    ])
    portal = make_franchise("Portal", [
        {"title": "Portal", "length_hours": 3, "release_year": 2007, "platforms": ["PC"], "play_on": "PC"},
    ])
    return {"zelda": zelda, "portal": portal}


@pytest.fixture(autouse=True)
def no_page_errors(request):
    """Fails a browser test if the page logs a JavaScript error."""
    if "page" not in request.fixturenames:
        yield
        return
    page: Page = request.getfixturevalue("page")
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    yield
    assert not errors, errors


def game(client, title):
    """A game as the API has it now."""
    for f in client.get("/api/franchises").json():
        for g in f["games"]:
            if g["title"] == title:
                return g
    raise AssertionError(f"no game {title!r}")


def load(page: Page):
    """Open the page and wait until the backlog is on screen (it's fetched after the page loads)."""
    page.goto("/")
    expect(page.locator(".fr").first).to_be_visible()


def franchise(page: Page, name: str):
    return page.locator(".fr").filter(has=page.locator(f'input.fr-title[value="{name}"]'))


def open_details(page: Page, name: str, title: str):
    block = franchise(page, name)
    block.locator(".fr-head .caret").click()
    block.locator(f'tr:has(input[data-field="title"][value="{title}"]) button.open-panel').click()
    expect(page.locator("#panel")).to_be_visible()


# ---------- the list ----------

def test_franchises_and_their_next_game(page: Page, backlog):
    load(page)
    expect(page.locator(".fr")).to_have_count(2)
    expect(franchise(page, "Zelda").locator(".fr-summary")).to_contain_text("1/2 done")
    expect(franchise(page, "Zelda").locator(".ondeck")).to_have_text("▶ A Link to the Past")
    expect(page.locator("#stats")).to_contain_text("3 games")


def test_editing_in_the_table_saves(page: Page, backlog, client):
    load(page)
    block = franchise(page, "Portal")
    block.locator(".fr-head .caret").click()
    block.locator('select[data-field="status"]').select_option("playing")
    expect(page.locator("#save-state")).to_contain_text("Saved")
    assert game(client, "Portal")["status"] == "playing"


def test_search_shows_only_matching_games(page: Page, backlog):
    load(page)
    page.locator("#search").fill("link")
    expect(page.locator(".fr")).to_have_count(1)
    expect(page.locator('.fr input[data-field="title"]')).to_have_count(1)
    expect(page.locator('.fr input[data-field="title"]')).to_have_value("A Link to the Past")


# ---------- the detail panel ----------

def test_panel_saves_changes(page: Page, backlog, client):
    load(page)
    open_details(page, "Zelda", "A Link to the Past")
    page.locator('#panel [name="length_hours"]').fill("16")
    page.locator('#panel [data-panel="save"]').click()
    expect(page.locator("#panel")).to_be_hidden()
    assert game(client, "A Link to the Past")["length_hours"] == 16


def test_panel_refuses_a_bad_length(page: Page, backlog, client):
    load(page)
    open_details(page, "Zelda", "A Link to the Past")
    page.locator('#panel [name="length_hours"]').fill("0")
    page.locator('#panel [data-panel="save"]').click()
    expect(page.locator('#panel [data-out="error"]')).to_contain_text("whole number of hours")
    expect(page.locator("#panel")).to_be_visible()
    assert game(client, "A Link to the Past")["length_hours"] == 15


def test_panel_asks_before_dropping_unsaved_changes(page: Page, backlog):
    load(page)
    open_details(page, "Zelda", "A Link to the Past")
    page.locator('#panel [name="title"]').fill("Changed")
    page.keyboard.press("Escape")
    expect(page.locator("#dialog")).to_contain_text("Discard your unsaved changes?")
    page.locator('#dialog [data-dialog="cancel"]').click()
    expect(page.locator("#panel")).to_be_visible()
    expect(page.locator('#panel [name="title"]')).to_have_value("Changed")


def test_length_lookup_fills_the_field(page: Page, backlog):
    # HowLongToBeat is never contacted: the page gets a canned answer.
    answer = {"matches": [{"name": "The Legend of Zelda: A Link to the Past", "year": 1991, "main_story": 14.95,
                           "hours": 15, "players": 563, "url": "https://howlongtobeat.com/game/1"}]}
    page.route("**/api/length-lookup?*", lambda route: route.fulfill(json=answer))
    load(page)
    open_details(page, "Zelda", "A Link to the Past")
    page.locator('#panel [name="length_hours"]').fill("")
    page.locator('[data-panel="lookup-length"]').click()
    page.get_by_role("button", name="Use 15 h").click()
    expect(page.locator('#panel [name="length_hours"]')).to_have_value("15")


# ---------- what to play next ----------

def test_picker_suggests_each_franchise_next_game(page: Page, backlog):
    load(page)
    page.locator('[data-action="pick"]').click()
    cards = page.locator(".pick-card .pick-game")
    expect(cards).to_have_count(2)
    assert sorted(cards.all_inner_texts()) == ["A Link to the Past", "Portal"]


def test_picker_filters(page: Page, backlog):
    load(page)
    page.locator('[data-action="pick"]').click()
    page.locator('[data-filter="length"]').select_option("short")
    expect(page.locator(".pick-card .pick-game")).to_have_text(["Portal"])
    page.locator('[data-filter="length"]').select_option("any")
    page.locator('[data-filter="series"]').select_option("continue")
    expect(page.locator(".pick-card .pick-game")).to_have_text(["A Link to the Past"])
    page.locator('[data-filter="playOn"]').select_option("PC")
    expect(page.locator("#picker")).to_contain_text("Nothing matches")


def test_picker_sets_a_game_playing(page: Page, backlog, client):
    load(page)
    page.locator('[data-action="pick"]').click()
    page.locator('[data-filter="playOn"]').select_option("PC")
    page.locator('[data-picker="playing"]').click()
    expect(page.locator("#toast")).to_contain_text("Now playing: Portal")
    assert game(client, "Portal")["status"] == "playing"


# ---------- stats ----------

def test_stats(page: Page, backlog):
    load(page)
    page.locator("#stats").click()
    stats = page.locator(".stats-modal")
    expect(stats.locator(".st-tile").first).to_contain_text("1")
    expect(stats.locator(".st-tile").first).to_contain_text("~8 h")
    expect(stats.locator(".st-tile").nth(2)).to_contain_text("~18 h")     # left: 15 + 3
    expect(stats.locator(".st-bar-row").first).to_contain_text("2025")
    stats.get_by_role("button", name="The Legend of Zelda").click()        # opens its details
    expect(page.locator('#panel [name="title"]')).to_have_value("The Legend of Zelda")


# ---------- phone ----------

def test_phone_layout_fits_the_screen(page: Page, backlog):
    page.set_viewport_size({"width": 375, "height": 812})
    load(page)
    franchise(page, "Zelda").locator(".fr-head .caret").click()
    fits = "document.documentElement.scrollWidth <= window.innerWidth"
    assert page.evaluate(fits), "the list scrolls sideways"
    page.locator("#stats").click()
    assert page.evaluate(fits), "the stats scroll sideways"
    tops = page.locator(".st-tile").evaluate_all("tiles => tiles.map(t => t.getBoundingClientRect().top)")
    assert tops[0] == tops[1] and tops[2] > tops[0], "stats tiles should be two by two"


def test_installable(page: Page):
    page.goto("/")
    manifest = page.evaluate("fetch(document.querySelector('link[rel=manifest]').href).then(r => r.json())")
    assert manifest["display"] == "standalone"
    assert json.dumps(manifest)  # parsed fine
