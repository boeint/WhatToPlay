# WhatToPlay rebuild — plan

## Decisions

| Topic | Decision |
|---|---|
| Backend | Python 3.14 + FastAPI (same stack as RomM, useful for a later RomM API integration) |
| Database | New `whattoplay` database + `whattoplay_dev` sandbox and a dedicated user on the existing MariaDB container. RomM's database is never touched. |
| Schema changes | Alembic migrations |
| Frontend | Plain HTML / CSS / JS (no framework, no build step), ported from `legacy/backlog.html` |
| Access | LAN-only, no login. Remote access via Unraid's VPN (Tailscale / WireGuard). |
| Deployment | Docker Compose (Compose Manager plugin) on Unraid; server pulls the private repo and builds the image |
| Data | Kept out of git. Initial data loaded through the app's own Import feature. |
| Portability | Nothing about a specific server lives in the code. Anyone with Docker and a MariaDB server can install it. |

## Configuration

| Kind of setting | Where it lives | Examples |
|---|---|---|
| Infrastructure | Environment variables, set in `.env` next to `docker-compose.yml` (never committed; the repo ships `.env.example` with placeholders) | Database host, port, name, user, password; the port the app listens on; the Docker network shared with MariaDB |
| App preferences | Settings page in the app, stored in the database | RomM URL and API key (later) |

Installation flow:
1. Create a database and user on your MariaDB (README gives the SQL; the app never needs MariaDB's admin password).
2. Copy `.env.example` to `.env` and fill it in.
3. `docker compose up -d` — the app creates or updates its own tables on startup.
4. Open the app — an empty database shows a first-run screen: **Import a backup** or **Start empty**.

One compose file is provided, for connecting to an existing MariaDB server.

## Phase 0 — Tools & repo
- [x] Install Git, GitHub CLI, Python 3.14
- [x] `gh auth login`, Git identity
- [x] Project structure, `.gitignore`, `.gitattributes`
- [x] Private GitHub repo + first push

## Phase 1 — Database
- [x] Find the MariaDB container and its Docker network on Unraid
- [x] Create `whattoplay` and `whattoplay_dev` databases, each with its own user that can only access that database
- [x] Design the tables (below)
- [ ] Python project setup (virtual environment, dependencies, config from environment variables)
- [ ] SQLAlchemy models + first Alembic migration, applied to `whattoplay_dev`

### Tables

| Table | Columns | Notes |
|---|---|---|
| `platforms` | id, name, sort_order | Initial list from the legacy app. A RomM platform code can be added later. |
| `franchises` | id, name, notes, sort_order, created_at, updated_at | |
| `games` | id, franchise_id, title, release_year, release_month, release_note, status, finished_on, notes, backloggd_url, sort_order, created_at, updated_at | Deleting a franchise deletes its games |
| `game_platforms` | game_id, platform_id, sort_order | One row per platform of a game |
| `game_links` | id, game_id, label, url, sort_order | One row per link |

- **Release date** is structured: `release_year` + optional `release_month` + optional `release_note` ("TBA", "Early Access"). Displayed as `Aug 2007`, `1998`, `2025 (Early Access)`.
- **Status** is limited to `unplayed`, `playing`, `finished`, `skip`.
- **`finished_on`**: set to today when a game becomes finished (if empty); editable by hand; cleared when the game leaves finished.
- **`backloggd_url`**: empty means the link is generated from the title.
- **`sort_order`**: rows have no inherent order in a database, so play order and display order are stored explicitly.

## Phase 2 — Backend (FastAPI, run locally against `whattoplay_dev`)
- [ ] Read everything; create / update / delete franchises and games; reorder
- [ ] Export / Import in a format designed for the new app (not the legacy export shape)
- [ ] Try every endpoint from the `/docs` page

## Phase 3 — Initial data
- [ ] One-off conversion of `data/seed.json` into the new import format
- [ ] Import into `whattoplay_dev`, verify: 97 franchises, 560 games, 34 finished, 2 playing, 11 game notes, 1 Backloggd override

## Phase 4 — Frontend
- [ ] Split into `index.html`, `styles.css`, `app.js`, `api.js`; drop the SEED
- [ ] Replace localStorage data saving with API calls (column widths / expanded franchises stay per-device in localStorage)
- [ ] Re-check every feature in HANDOFF §2

## Phase 5 — Deploy to Unraid
- [ ] `Dockerfile`, `docker-compose.yml`, `.env.example`
- [ ] Run database migrations automatically on startup; first-run screen (Import a backup / Start empty)
- [ ] Compose Manager, read-only deploy key, clone, `.env`, Compose Up
- [ ] Import real data into `whattoplay`; test from phone and PC

## Phase 6 — Safety net & docs
- [ ] Database backups (Appdata Backup plugin or scheduled dump)
- [ ] README: update, restore, run locally

## Later (optional)
- Settings page (app preferences stored in the database)
- RomM API integration
- GitHub Actions building the image (deployment option B)
