<p align="center"><img src="app/static/icon.png" width="96" alt=""></p>

# WhatToPlay

A self-hosted video-game backlog manager.

- Games are grouped into **franchises** and kept in **play order**.
- **What to play next** picks a random franchise and suggests its next game — never a sequel
  before you've finished the earlier game, never an unreleased (TBA) game.
- Status (unplayed / playing / finished / skip), finished date, release date, platforms and the
  one you'll **play on**, notes, links, and a link to each game's Backloggd page.
- Search (titles, platforms, notes), filters, sorting, drag-and-drop ordering.
- Works on desktop and phone. Export / import of all data as a JSON backup.

It runs as one small container and stores its data in a MariaDB (or MySQL) database you already
have. No account or login: it's meant for your home network (use a VPN such as Tailscale or
WireGuard to reach it from outside).

## Install

### 1. Create a database and a user

On your MariaDB server, run this once (for example in Adminer or phpMyAdmin), with a password of your
choice. The user can only access its own database.

```sql
CREATE DATABASE whattoplay CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'whattoplay'@'%' IDENTIFIED BY 'choose-a-password';
GRANT ALL PRIVILEGES ON whattoplay.* TO 'whattoplay'@'%';
```

### 2a. Unraid

1. Get the template [`unraid/whattoplay.xml`](unraid/whattoplay.xml) onto the flash drive, in
   `config/plugins/dockerMan/templates-user/`. Without a terminal: **Main ▸ Flash ▸ SMB Security
   Settings ▸ Export: Yes**, then copy the file to `\\your-server\flash\config\plugins\dockerMan\templates-user\`.
2. **Docker ▸ Add Container ▸ Template: WhatToPlay.**
3. **Network Type:** the network your MariaDB container is on, so `DB_HOST` can be its container name.
4. Fill in the database password and click **Apply**.

Updates appear in the Docker tab like any other container.

### 2b. Docker Compose

Copy [`docker-compose.yml`](docker-compose.yml) and [`.env.example`](.env.example) (renamed to
`.env`), fill in `.env`, then `docker compose up -d`.

### 3. First start

The container waits for the database, creates its tables, and starts on port **8095** (or the one
you chose). An empty backlog offers to **import a backup** or to start with a new franchise.

## Configuration

| Variable | Default | |
|---|---|---|
| `DB_HOST` | — | Database server (container name or IP) |
| `DB_PORT` | `3306` | |
| `DB_NAME` | — | Database created for WhatToPlay |
| `DB_USER` | — | User created for WhatToPlay |
| `DB_PASSWORD` | — | That user's password |
| `TZ` | `UTC` | Time zone, used for "finished on" dates (Unraid sets it automatically) |

## Development

Python 3.14, FastAPI, SQLAlchemy, Alembic; the page is plain HTML / CSS / JavaScript.

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows; .venv/bin/... elsewhere
cp .env.example .env                                       # point it at a development database
alembic upgrade head
uvicorn app.main:app                                       # http://localhost:8000, API docs at /docs
```

Pushes to `main` publish `ghcr.io/boeint/whattoplay:dev`; release tags (`v1.2.3`) publish `:latest`.
The design notes and roadmap are in [PLAN.md](PLAN.md).

## License

[MIT](LICENSE)
