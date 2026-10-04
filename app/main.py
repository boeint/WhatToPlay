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

from app import backups
from app.backups import backup_loop, backup_status
from app.db import get_engine
from app.mcp_server import AISwitch, mcp, mcp_asgi_app
from app.routers import backup, franchises, games, platforms, settings

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs while the app is up: the daily backup task and the MCP session manager."""
    task = asyncio.create_task(backup_loop())
    async with mcp.session_manager.run():   # a mounted app's own start-up never runs
        yield
    task.cancel()


app = FastAPI(title="WhatToPlay", version="1.3.1", lifespan=lifespan)

app.include_router(platforms.router)
app.include_router(franchises.router)
app.include_router(games.router)
app.include_router(backup.router)
app.include_router(backups.router)
app.include_router(settings.router)


@app.get("/api/health", tags=["health"])
def health():
    """Used by Docker / Unraid to show whether the app is healthy.

    Backups are reported but don't make the app "unhealthy": it still works without them.
    """
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        return JSONResponse(status_code=503, content={"status": "error", "database": "unreachable"})
    status_ = backup_status(with_files=False)
    return {
        "status": "ok",
        "database": "ok",
        "backups": {
            "enabled": status_["enabled"],
            "latest": status_["latest"]["written_at"] if status_["latest"] else None,
            "last_error": status_["last_error"],
        },
    }


# The AI assistant's MCP endpoint (refused unless switched on in Settings).
app.mount("/mcp", AISwitch(mcp_asgi_app), name="mcp")

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
