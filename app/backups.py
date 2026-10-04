"""Daily backups: write an export file to a folder every day and keep the newest few.

Runs inside the web app as a background task. Enabled when the backup folder
(BACKUP_DIR, default /backups) exists and is writable — in Docker, when a folder
is mapped there. A backup is also made at start-up if today's file is missing,
so a night with the container down doesn't leave a gap.

Also: the backup status and list (GET /api/backups), and restoring one of them
(POST /api/backups/{name}/restore), which first saves a copy of the current data.
"""
import asyncio
import logging
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine
from app.deps import SessionDep
from app.routers.backup import EXPORT_PREFIX, build_export, export_filename, replace_all, require_replace
from app.schemas import ExportFile

log = logging.getLogger("uvicorn.error")   # shows up in the container log with uvicorn's own lines
router = APIRouter(tags=["backup"])

SAFETY_PREFIX = "whattoplay-before-restore-"
SAFETY_KEEP = 10
# Only these names can be listed or restored (no other file on the server is reachable).
BACKUP_NAME = re.compile(r"^whattoplay-(export|before-restore)-[0-9-]+\.json$")

# The last failure, if any (successes are read from the files themselves).
last_error: dict | None = None


def folder_state() -> tuple[Path | None, str | None]:
    """(folder, None) when backups are on, or (None, reason) when they're off."""
    folder = Path(get_settings().backup_dir)
    if not folder.is_dir():
        return None, f"no folder at {folder} (map one to enable backups)"
    if not os.access(folder, os.W_OK):
        return None, f"{folder} is not writable"
    return folder, None


def write_file(path: Path, text: str) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)              # all at once: never a half-written backup file


def prune(folder: Path, prefix: str, keep: int) -> None:
    for old in sorted(folder.glob(f"{prefix}*.json"))[:-keep]:   # the date in the name sorts them
        old.unlink()


def write_backup(folder: Path) -> Path:
    """Write today's export file (replacing an earlier one from today) and prune old ones."""
    with Session(get_engine()) as session:
        text = build_export(session)
    target = folder / export_filename()
    write_file(target, text)
    prune(folder, EXPORT_PREFIX, get_settings().backup_keep)
    return target


def seconds_until(hhmm: str) -> float:
    """Seconds from now until the next HH:MM (local time)."""
    return (next_run(hhmm) - datetime.now()).total_seconds()


def next_run(hhmm: str) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


async def run_backup(folder: Path) -> None:
    global last_error
    try:
        path = await asyncio.to_thread(write_backup, folder)
        last_error = None
        log.info("Backup written: %s", path)
    except Exception as exc:   # a failed backup must never take the app down
        last_error = {"at": datetime.now().astimezone().isoformat(timespec="seconds"), "message": str(exc)}
        log.exception("Backup failed")


async def backup_loop() -> None:
    folder, reason = folder_state()
    if folder is None:
        log.info("Daily backups are off: %s.", reason)
        return
    settings = get_settings()
    log.info("Daily backups on: %s, every day at %s, keeping %d.",
             folder, settings.backup_time, settings.backup_keep)
    if not (folder / export_filename(date.today())).exists():
        await run_backup(folder)
    while True:
        await asyncio.sleep(seconds_until(settings.backup_time))
        await run_backup(folder)


# ---------- status, list, restore ----------
def file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "kind": "before-restore" if path.name.startswith(SAFETY_PREFIX) else "daily",
        "size": stat.st_size,
        "written_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
    }


def backup_status(with_files: bool = True) -> dict:
    settings = get_settings()
    folder, reason = folder_state()
    files = []
    if folder is not None:
        files = sorted((file_info(p) for p in folder.glob("whattoplay-*.json") if BACKUP_NAME.match(p.name)),
                       key=lambda f: f["written_at"], reverse=True)
    daily = [f for f in files if f["kind"] == "daily"]
    result = {
        "enabled": folder is not None,
        "reason": reason,
        "time": settings.backup_time,
        "keep": settings.backup_keep,
        "next_at": next_run(settings.backup_time).astimezone().isoformat(timespec="seconds") if folder else None,
        "latest": daily[0] if daily else None,
        "daily_count": len(daily),
        "last_error": last_error,
    }
    if with_files:
        result["files"] = files
    return result


@router.get("/api/backups")
def list_backups():
    """Backup status, and the backup files available on the server (newest first)."""
    return backup_status()


@router.post("/api/backups/{name}/restore")
def restore_backup(name: str, session: SessionDep, replace: bool = False):
    """Replace everything with one of the server's backup files.

    A copy of the current data is saved first (as whattoplay-before-restore-…json in
    the same folder), so a restore can itself be undone. Requires `?replace=true`.
    """
    require_replace(replace)
    folder, reason = folder_state()
    if folder is None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Backups are off: {reason}")
    path = folder / name
    if not BACKUP_NAME.match(name) or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No backup named {name}")
    try:
        data = ExportFile.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{name} is not a valid backup: {exc}")

    safety = folder / f"{SAFETY_PREFIX}{datetime.now():%Y-%m-%d-%H%M%S}.json"
    write_file(safety, build_export(session))
    prune(folder, SAFETY_PREFIX, SAFETY_KEEP)
    counts = replace_all(session, data)
    log.info("Restored %s (copy of the previous data: %s)", name, safety.name)
    return {**counts, "restored": name, "previous_data_saved_as": safety.name}
