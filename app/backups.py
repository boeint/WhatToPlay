"""Daily backups: write an export file to a folder every day and keep the newest few.

Runs inside the web app as a background task. Enabled when the backup folder
(BACKUP_DIR, default /backups) exists and is writable — in Docker, when a folder
is mapped there. A backup is also made at start-up if today's file is missing,
so a night with the container down doesn't leave a gap.
"""
import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine
from app.routers.backup import EXPORT_PREFIX, build_export, export_filename

log = logging.getLogger("uvicorn.error")   # shows up in the container log with uvicorn's own lines


def backup_folder() -> Path | None:
    """The backup folder, or None (with the reason logged) when backups are off."""
    folder = Path(get_settings().backup_dir)
    if not folder.is_dir():
        log.info("Daily backups are off: no folder at %s (map one to enable them).", folder)
        return None
    if not os.access(folder, os.W_OK):
        log.warning("Daily backups are off: %s is not writable.", folder)
        return None
    return folder


def write_backup(folder: Path) -> Path:
    """Write today's export file (replacing an earlier one from today) and prune old ones."""
    with Session(get_engine()) as session:
        text = build_export(session)
    target = folder / export_filename()
    temporary = target.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(target)            # all at once: never a half-written backup file

    keep = get_settings().backup_keep
    files = sorted(folder.glob(f"{EXPORT_PREFIX}*.json"))   # the date in the name sorts them
    for old in files[:-keep]:
        old.unlink()
    return target


def seconds_until(hhmm: str) -> float:
    """Seconds from now until the next HH:MM (local time)."""
    hour, minute = map(int, hhmm.split(":"))
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def run_backup(folder: Path) -> None:
    try:
        path = await asyncio.to_thread(write_backup, folder)
        log.info("Backup written: %s", path)
    except Exception:   # a failed backup must never take the app down
        log.exception("Backup failed")


async def backup_loop() -> None:
    folder = backup_folder()
    if folder is None:
        return
    settings = get_settings()
    log.info("Daily backups on: %s, every day at %s, keeping %d.",
             folder, settings.backup_time, settings.backup_keep)
    if not (folder / export_filename(date.today())).exists():
        await run_backup(folder)
    while True:
        await asyncio.sleep(seconds_until(settings.backup_time))
        await run_backup(folder)
