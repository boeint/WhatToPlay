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

## Phase 0 — Tools & repo
- [x] Install Git, GitHub CLI, Python 3.14
- [x] `gh auth login`, Git identity
- [x] Project structure, `.gitignore`, `.gitattributes`
- [x] Private GitHub repo + first push

## Phase 1 — Database
- [ ] Find the MariaDB container and its Docker network on Unraid
- [ ] Create `whattoplay` and `whattoplay_dev` databases and a `whattoplay` user (admin password typed by the user, never stored in the repo)
- [ ] Tables: `franchises`, `games`, `game_platforms`, `game_links` — each with explicit `sort_order`
- [ ] First Alembic migration

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
- [ ] Compose Manager, read-only deploy key, clone, `.env`, Compose Up
- [ ] Import real data into `whattoplay`; test from phone and PC

## Phase 6 — Safety net & docs
- [ ] Database backups (Appdata Backup plugin or scheduled dump)
- [ ] README: update, restore, run locally

## Later (optional)
- RomM API integration
- GitHub Actions building the image (deployment option B)
