# WhatToPlay rebuild — plan

## Decisions

| Topic | Decision |
|---|---|
| Backend | Python 3.14 + FastAPI (same stack as RomM, useful for a later RomM API integration) |
| Database | New `whattoplay` database + `whattoplay_dev` sandbox and a dedicated user on the existing MariaDB container. RomM's database is never touched. |
| Schema changes | Alembic migrations |
| Frontend | Plain HTML / CSS / JS (no framework, no build step), ported from `legacy/backlog.html` |
| Access | LAN-only, no login. Remote access via Unraid's VPN (Tailscale / WireGuard). |
| Deployment | GitHub Actions builds and tests the image and publishes it to ghcr.io (public). Installed on Unraid from the web UI with a template (`unraid/whattoplay.xml`) — no terminal. Pushes to `main` publish `:dev`; release tags (`v1.2.3`) publish `:latest`, which the server follows. |
| Data | Kept out of git. Initial data loaded through the app's own Import feature. |
| Portability | Nothing about a specific server lives in the code. Anyone with Docker and a MariaDB server can install it. |

## Configuration

| Kind of setting | Where it lives | Examples |
|---|---|---|
| Infrastructure | Container environment variables: prompted by the Unraid template (or `.env` for local development / docker compose) | Database host, port, name, user, password. Port and network are chosen in Unraid's form. `TZ` is passed by Unraid automatically. |
| App preferences | Settings page in the app, stored in the database | RomM URL and API key (later) |

Installation flow (Unraid, all in the web UI):
1. Create a database and user on your MariaDB (README gives the SQL, which can be run in Adminer; the app never needs MariaDB's admin password).
2. Docker ▸ Add Container ▸ Template **WhatToPlay**; pick the network your MariaDB is on; fill in the database password.
3. The container waits for the database, creates or updates its own tables, then starts.
4. Open the app — an empty database shows a first-run screen: **Import a backup** or **start with a new franchise**.

## Phase 0 — Tools & repo
- [x] Install Git, GitHub CLI, Python 3.14
- [x] `gh auth login`, Git identity
- [x] Project structure, `.gitignore`, `.gitattributes`
- [x] Private GitHub repo + first push

## Phase 1 — Database
- [x] Find the MariaDB container and its Docker network on Unraid
- [x] Create `whattoplay` and `whattoplay_dev` databases, each with its own user that can only access that database
- [x] Design the tables (below)
- [x] Python project setup (virtual environment, dependencies, config from environment variables)
- [x] SQLAlchemy models + first Alembic migration, applied to `whattoplay_dev`

### Tables

| Table | Columns | Notes |
|---|---|---|
| `platforms` | id, name, sort_order | Initial list from the legacy app. A RomM platform code can be added later. |
| `franchises` | id, name, notes, sort_order, created_at, updated_at | |
| `games` | id, franchise_id, title, release_year, release_month, release_tba, status, finished_on, notes, backloggd_url, play_on_id, sort_order, created_at, updated_at | Deleting a franchise deletes its games |
| `game_platforms` | game_id, platform_id, sort_order | One row per platform of a game |
| `game_links` | id, game_id, label, url, sort_order | One row per link |

- **Release date** is the full launch date (not early access), structured as `release_year` + optional `release_month`. `release_tba` marks a date that isn't final (a year, if set, is the expected one). Displayed as `Aug 2007`, `1998`, `2026 (TBA)`, `TBA`.
- **Status** is limited to `unplayed`, `playing`, `finished`, `skip`.
- **`finished_on`**: set to today when a game becomes finished (if empty); editable by hand; cleared when the game leaves finished.
- **`backloggd_url`**: empty means the link is generated from the title.
- **Platforms vs Play on**: `game_platforms` lists everywhere the game is available; `play_on_id` is the one you'll play it on (must be one of them, cleared if that platform is removed).
- **`sort_order`**: rows have no inherent order in a database, so play order and display order are stored explicitly.

## Phase 2 — Backend (FastAPI, run locally against `whattoplay_dev`)
- [x] Read everything; create / update / delete franchises and games; reorder
- [x] Export / Import in a format designed for the new app (not the legacy export shape)
- [ ] Try every endpoint from the `/docs` page

## Phase 3 — Initial data
- [x] One-off conversion of `data/seed.json` into the new import format (`data/import-initial.json`, not committed)
- [x] Import into `whattoplay_dev`, verify: 97 franchises, 560 games, 34 finished, 2 playing, 7 TBA, 11 game notes, 1 Backloggd override

## Phase 4 — Frontend
- [x] Split into `index.html`, `styles.css`, `app.js`, `api.js`; drop the SEED (step 1: read-only list)
- [x] Step 2: quick edits in the table (title, status, play on, notes, franchise name/notes), "Saved" indicator, error handling
- [x] Step 3: game detail panel (release year/month/TBA, finished date, platforms, notes, links, Backloggd override, move to franchise)
- [x] Step 4: add game (opens the panel), add franchise dialog, in-app delete confirmations, reorder arrows + drag and drop
- [x] Step 5: search (incl. notes), status filter, sorts (custom sort: drag franchises), column resizing
- [x] Step 6: "What to play next" picker, skipping franchises whose next game is TBA or already being played
- [x] Step 7: Export / Import buttons, automatic backup before import
- [x] Step 8: phone layout (cards, full-screen panel); reload data when returning to the tab
- [x] Re-check every feature in HANDOFF §2 (the legacy app is inspiration, not the spec: improve where it makes sense)

## Phase 5 — Deploy to Unraid
- [x] `Dockerfile` (non-root, health check), start script (waits for the database, runs migrations), first-run screen
- [x] GitHub Actions: build, test against a throwaway MariaDB, publish to ghcr.io
- [x] Unraid template `unraid/whattoplay.xml`
- [x] Make the repository public (MIT license, README with install instructions)
- [x] Make the image public (GitHub ▸ package settings ▸ Change visibility; no API for it)
- [x] First release `v1.0.0` → `:latest`
- [ ] Unraid: export the flash share, copy the template, Add Container from the template
- [ ] Import real data into `whattoplay`; test from phone and PC
- [x] `docker-compose.yml` example for installs outside Unraid

## Phase 6 — Safety net & docs
- [ ] Database backups (Appdata Backup plugin or scheduled dump)
- [ ] README: update, restore, run locally

## Phase 7 — AI assistant (MCP)
Ask Claude (Desktop / Code) "add the Resident Evil franchise": it researches, checks for duplicates,
shows the proposed list for approval, then writes it through the app's tools.
- [ ] MCP server exposing tools over the existing API: list/find, get preferences, add franchise with its games (one transaction), update game
- [ ] "AI instructions" note in a Settings page (platform preferences, what to skip, remakes, DLC…), read by the AI every time
- [ ] Games the AI decides to skip are still added, with status Skip and a note explaining why
- [ ] Remember each game's metadata source id (e.g. IGDB) for duplicate checks and the TBA date scan
- Later option: an "Add with AI" box inside the app (Claude API key, works from the phone)

## Later (optional)
- Settings page (app preferences stored in the database)
- Release date scan: re-check games flagged `release_tba` against a metadata source and fill in confirmed dates
- RomM API integration
- GitHub Actions building the image (deployment option B)
