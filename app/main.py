"""The WhatToPlay web app.

Run locally:
    uvicorn app.main:app
then open http://localhost:8000/docs
"""
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.routers import backup, franchises, games, platforms

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="WhatToPlay", version="0.1.0")

app.include_router(platforms.router)
app.include_router(franchises.router)
app.include_router(games.router)
app.include_router(backup.router)

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
