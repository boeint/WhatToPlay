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

## AI assistant (optional)

WhatToPlay includes an [MCP](https://modelcontextprotocol.io) server, so an AI assistant can read your
backlog and add franchises and games for you: *"add the Resident Evil franchise"* → it researches the
series, shows you the proposed list, and adds it once you approve.

1. In the app: **⚙ Settings ▸ AI assistant** (off by default) and adjust the **AI instructions**
   (which games to include, how to pick "Play on", etc.).
2. In Claude Code, add the server: `claude mcp add --transport http whattoplay http://your-server:8095/mcp/`

Only clients on your network can reach it (claude.ai's own connectors connect from the internet). While
the switch is off, `/mcp` refuses every request. Writes go through the same validation as the app.

## Backups and restore

- **Daily backups:** every day at `BACKUP_TIME` the app writes `whattoplay-export-YYYY-MM-DD.json` to
  the folder mapped to `/backups` (on Unraid: `/mnt/user/appdata/whattoplay/backups` by default) and
  keeps the newest `BACKUP_KEEP` files. One is also written at start-up if today's is missing.
- **Manual backup:** the **Export** button downloads the same file.
- **Status:** the bottom of the page shows the last backup and the next one, or a warning if backups
  are off or the last one failed.
- **Restore from the server:** **Restore a backup…** (bottom of the page) lists the backup files; the
  current data is first saved in the same folder as `whattoplay-before-restore-….json`, so a restore can
  be undone from the same list.
- **Restore from a file:** **Import** ▸ choose a backup file (a backup of the current data is downloaded
  first). If a file is rejected, nothing is changed.

## Updating

On Unraid, the Docker tab shows an update when a new release is published: click **Apply Update**.
The container applies any database changes on start-up; your data is kept. With Docker Compose:
`docker compose pull && docker compose up -d`.

## Configuration

| Variable | Default | |
|---|---|---|
| `DB_HOST` | — | Database server (container name or IP) |
| `DB_PORT` | `3306` | |
| `DB_NAME` | — | Database created for WhatToPlay |
| `DB_USER` | — | User created for WhatToPlay |
| `DB_PASSWORD` | — | That user's password |
| `TZ` | `UTC` | Time zone, used for "finished on" dates and the backup time (Unraid sets it automatically) |
| `BACKUP_DIR` | `/backups` | Folder for daily backups; backups are off if it doesn't exist |
| `BACKUP_KEEP` | `30` | Number of daily backup files to keep |
| `BACKUP_TIME` | `03:30` | Time of the daily backup (HH:MM) |
| `PUID` / `PGID` | `99` / `100` | User and group the app runs as (owner of the backup files) |

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
