# WhatToPlay: notes for Claude

A self-hosted video-game backlog: franchises containing games in play order, a "what to play
next" picker, stats. FastAPI + MariaDB backend, plain-JS frontend, one Docker image. User-facing
docs are in [README.md](README.md); the original design and roadmap are in [PLAN.md](PLAN.md).

## Layout

- `app/main.py`: the FastAPI app (version string, routers, `/api/health`, `/mcp` mount, static files at `/`).
- `app/models.py` (SQLAlchemy 2), `app/schemas.py` (Pydantic v2: `GameCreate`/`GameUpdate`/`GameOut`, export file).
- `app/routers/`: REST API. `games.py`'s `apply_fields` holds the shared game rules (finished date, Play on).
- `app/mcp_server.py`: MCP tools for the AI assistant, gated by the Settings switch (`AISwitch`).
- `app/preferences.py`: settings with defaults, including `DEFAULT_AI_INSTRUCTIONS`. The live instructions
  are user-edited data in the `settings` table, not code.
- `app/backups.py` (daily export files + restore), `app/lengths.py` (HowLongToBeat lookup via `howlongtobeatpy`).
- `app/static/`: ES modules, no build step. `app.js` (list, edits), `panel.js` (detail panel), `picker.js`,
  `stats.js`, `dialog.js`, `rating.js` (stars, devices), `api.js` (the only file that calls the backend).
- `alembic/versions/`: migrations, applied automatically on container start (`docker/start.sh`).
- `tests/`: pytest against a real MariaDB; `test_browser.py` drives the page in Chromium (Playwright).

## Commands

```sh
.venv/Scripts/python -m pytest                       # all tests (~3-4 min; DB name must end in _test)
.venv/Scripts/python -m pytest tests/test_browser.py # page tests only
.venv/Scripts/python -m alembic revision --autogenerate -m "..."   # then READ and fix the file
.venv/Scripts/python -m alembic upgrade head         # dev database
.venv/Scripts/uvicorn app.main:app --port 8000       # dev server (no --reload: it hangs on this PC)
```

Configuration comes from environment variables / `.env` (see `.env.example`). Never hardcode a
server, password or path: the app must stay installable by anyone.

## Conventions and pitfalls

- **Migrations:** autogenerate does not detect CHECK constraints. Add them by hand
  (`op.create_check_constraint(op.f("ck_games_..."), ...)`) and drop them in `downgrade`.
- **New game fields** touch: the model, a migration, `GameOut` + `from_model`, `GameCreate` + `from_model`
  (this also puts them in exports), `GameUpdate`, the panel (`readForm`), and tests (API, export round trip).
- **Names compare ignoring case and accents** (MariaDB `utf8mb4_unicode_ci`); `name_key()` does the same in Python.
- **CSS:** the phone layout `@media (max-width: 760px)` block must stay **last** in `styles.css`.
  `[hidden]{display:none!important}` is relied on.
- **Page edits** use `data-field` (saved on change by one listener in `app.js`) and `data-action` (one click
  listener). Panel fields use `name=` instead, so the table listener ignores them.
- **MCP library is v2** (`mcp==2.x`): `from mcp.server import MCPServer`; raise
  `mcp.server.mcpserver.exceptions.ToolError` (other exceptions don't reach the client); return lists
  wrapped in an object. The endpoint is `/mcp/` (trailing slash).
- **HowLongToBeat has no official API.** `howlongtobeatpy` may break when the site changes; the lookup
  must fail with a clear message, never break the page. Tests replace it with a fake (never online).
- **Browser tests:** open the page with `load(page)`, which waits for the list (it's fetched after page
  load). Any JS console error fails a test. They run in a thread with an event loop, so async helpers in
  other tests run in their own thread (see `call_tool`).
- Release dates: `release_year` + optional `release_month` + `release_tba`. A month needs a year.
- Status rules: `finished_on` is set to today when a game becomes finished (unless given) and cleared
  when it stops being finished.

## Releasing

1. Bump `version=` in `app/main.py`; tests pass.
2. Commit and push to `main` → GitHub Actions runs the tests, then builds and publishes `ghcr.io/boeint/whattoplay:dev`.
3. `git tag -a vX.Y.Z -m "..."` and push the tag → `:latest` and semver tags.
4. The user updates the container from the Unraid web UI (no terminal).

Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Working with the user's data

The live backlog is changed through the MCP tools (`mcp__whattoplay__*`) or the REST API, and only after
the user approved the complete proposed change. Call `get_instructions` first: it returns the user's own
rules (play order, platforms, Play on, lengths from HowLongToBeat "Main Story", TBA, Skip...).
