# WhatToPlay — Project Handoff for Claude Code

This document hands off a working personal project so it can be rebuilt as a
proper client/server web app. Read it fully before starting.

## 1. What this is
A personal **video-game backlog manager**. Games are grouped into **franchises**;
within a franchise they are kept in **play order**. The signature feature is a
**"What to play next" picker**: it looks at each franchise, finds the first game
that is not Finished or Skipped (respecting order), and randomly picks one of those
across all franchises — so it never suggests Final Fantasy VI if you haven't
finished Final Fantasy III yet.

The current version is a single self-contained file, `backlog.html`, that stores
all user data in the browser's **localStorage**. It works, but the data is trapped
in one browser on one machine. The goal (section 4) is to centralize it.

## 2. Current features / behaviors to preserve
- Franchises (collapsible; **collapsed by default on every load**) containing games.
- Franchises are sorted **A–Z by default** (literal first word, "The" counts).
  Other sorts: custom order, most-remaining.
- Per game: **title, release month/year, platform(s), status, notes, links**.
- Per franchise: a **notes** field.
- **Status**: unplayed / playing / finished / skip. Header shows "X/Y done" and a
  green "next up" pill for the franchise's on-deck game (no row highlight).
- **Platform is a multi-select** from a fixed list (PC, PS5…NES, Game Boy, etc.),
  shown as chips. Not free text.
- **"What to play next"** modal: random pick = first non-finished/non-skip game of
  a randomly chosen eligible franchise; can scope to one franchise, re-roll, or mark
  the pick as Playing.
- **Backloggd link per game**: a small favicon badge opens the game's Backloggd page.
  URL is auto-generated from the title (slug rules), but a manual backloggd.com link
  added in a game's Links **overrides** it and is removed from the visible link list
  (stored separately as the game's `bl` field).
- **Columns are resizable** (drag header edges); widths shared across all franchises
  and persisted. Title column auto-absorbs remaining width.
- **Search** (title/platform/franchise) and **status filter** — the status filter
  hides franchises with no matching game and auto-expands the ones that remain.
- Up/down arrows to reorder games within a franchise (far right of each row).
- **Export / Import** of all data as JSON (this is how data is migrated — see §3).
- Reorder arrows live just before a red delete (×). Add/delete games & franchises.
- Visual: dark theme; game list sits in an inset framed table, lighter background,
  purple bar down its left edge; franchise title is medium-weight ~18px (not bold).

## 3. Data model (and the exact shape of the exported JSON)
The app's state is an array of franchises. The **Export** button writes this array
to a JSON file — that file is the real user data to migrate into the database.

```
[
  {
    "id": "f0_seed",
    "name": "BioShock",
    "notes": "",
    "games": [
      {
        "id": "g_ab12cd3",
        "title": "BioShock",
        "released": "Aug 2007",          // free text, usually "Mon YYYY" or "YYYY"
        "platform": ["PC","PS4","Switch"],// array of tags from a fixed list
        "status": "unplayed",            // unplayed | playing | finished | skip
        "notes": "",
        "links": [ {"label":"review","url":"https://..."} ],
        "bl": "https://backloggd.com/games/bioshock/"  // optional manual override
      }
    ]
  }
]
```
Order of franchises and of games within each franchise is meaningful (play order).
A suggested relational schema: `franchises(id, name, notes, sort_order)` and
`games(id, franchise_id, title, released, platform_json_or_jointable, status,
notes, bl_url, sort_order)` plus a `links` table or JSON column. Preserve ordering
with an explicit sort_order column.

`backlog.html` also contains a hardcoded `SEED` array (the ~97 franchises / ~560
games shipped as defaults). The **exported JSON is the source of truth** for the
user's actual data (their statuses, notes, custom links); the SEED is only the
original defaults and can be ignored once the JSON is imported.

## 4. Target architecture (goals — decide specifics in Claude Code)
- **Centralized**, accessible from any device on the user's network.
- Backed by **MariaDB**. The user already runs a MariaDB **Docker container on an
  Unraid server** (used by another app, RomM). **Create a NEW, separate database and
  DB user for this app — do NOT touch RomM's database.**
- Deployed on **Unraid** (Docker). The app container connects to the existing MariaDB
  container over Docker networking.
- Source code kept in a **private GitHub repo**.
- The existing `backlog.html` frontend can be **reused almost as-is**; the main change
  is replacing localStorage reads/writes with calls to a small backend REST API.

## 5. Open decisions to make WITH the user in Claude Code
- **Backend stack** (e.g. Node.js/Express, Python/FastAPI, or PHP). Not yet decided.
- **Auth & exposure**: LAN-only (no login), LAN + single password, or
  internet-accessible via reverse proxy (user may have SWAG / Nginx Proxy Manager)
  with login. Not yet decided.
- **Deployment mechanics** on Unraid (docker-compose stack vs. container template).
- MariaDB connection details (Unraid host IP, port, admin credentials to create the
  new DB + user) — the user will need to provide these during setup.

## 6. Files in this handoff
- `backlog.html` — the complete current app (UI + logic + SEED defaults). Reference it
  for exact behavior/visuals to reproduce, and to port the frontend.
- `game-backlog-YYYY-MM-DD.json` — the user's **exported live data** (they produce this
  by clicking Export in backlog.html). This is what gets imported into MariaDB.
- `HANDOFF.md` — this document.

## 7. The user
Not a professional developer. Prefers clear, step-by-step guidance and plain
explanations of trade-offs. Happy to run commands when told exactly what to run.
