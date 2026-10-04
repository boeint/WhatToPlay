"""The WhatToPlay web app.

Run locally:
    uvicorn app.main:app
then open http://localhost:8000/docs
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.backups import backup_loop
from app.db import get_engine
from app.routers import backup, franchises, games, platforms

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs while the app is up: starts the daily backup task, stops it on shutdown."""
    task = asyncio.create_task(backup_loop())
    yield
    task.cancel()


app = FastAPI(title="WhatToPlay", version="1.1.0", lifespan=lifespan)

app.include_router(platforms.router)
app.include_router(franchises.router)
app.include_router(games.router)
app.include_router(backup.router)


@app.get("/api/health", tags=["health"])
def health():
    """Used by Docker / Unraid to show whether the app is healthy."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        return JSONResponse(status_code=503, content={"status": "error", "database": "unreachable"})
    return {"status": "ok", "database": "ok"}


# The web page (index.html, styles.css, app.js...) at "/". Mounted last so the
# /api/... routes above take precedence.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


@app.exception_handler(IntegrityError)
def database_conflict(request: Request, exc: IntegrityError) -> JSONResponse:
    """Safety net: the database refused a change (duplicate, missing reference...).

    Endpoints check the usual cases themselves with clearer messages; this turns
    anything unforeseen into a 409 instead of a 500. The request's transaction is
    rolled back, so nothing was changed.
    """
    reason = exc.orig.args[1] if exc.orig is not None and len(exc.orig.args) > 1 else str(exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": f"Conflicts with existing data, nothing was changed: {reason}"},
    )
