# WhatToPlay

A personal video-game backlog manager. Games are grouped into franchises and kept
in play order; the **"What to play next"** picker suggests the next unfinished game
from a random franchise.

This is a rebuild of a single-file browser app (`legacy/backlog.html`) into a
centralized web app:

- **Backend:** Python 3.14 + FastAPI
- **Database:** MariaDB (separate `whattoplay` database on the existing Unraid container)
- **Frontend:** plain HTML / CSS / JavaScript
- **Hosting:** Docker Compose on Unraid, LAN-only

See [PLAN.md](PLAN.md) for the build plan and [HANDOFF.md](HANDOFF.md) for the
original feature list and data model.

## Repository layout

| Path | What it is |
|---|---|
| `legacy/backlog.html` | The original app, kept as a reference for features and visuals |
| `data/` | Local data files (exports, initial import). **Not committed** — see `.gitignore` |
| `PLAN.md` | Phased build plan |
| `HANDOFF.md` | Original project handoff |

_Setup, run and deploy instructions will be added as the app is built._
