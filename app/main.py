"""The WhatToPlay web app.

Run locally:
    uvicorn app.main:app --reload
then open http://localhost:8000/docs
"""
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Franchise, Game, GamePlatform, Platform
from app.schemas import FranchiseOut, PlatformOut

app = FastAPI(title="WhatToPlay", version="0.1.0")

# "Give this endpoint a database session" — FastAPI calls get_session for us.
SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/api/platforms", response_model=list[PlatformOut])
def list_platforms(session: SessionDep):
    """All platforms, in display order."""
    return session.scalars(select(Platform).order_by(Platform.sort_order)).all()


@app.get("/api/franchises", response_model=list[FranchiseOut])
def list_franchises(session: SessionDep):
    """All franchises in order, each with its games in play order."""
    # selectinload: fetch all games / platforms / links in a few bulk queries
    # instead of one query per franchise and per game.
    query = (
        select(Franchise)
        .order_by(Franchise.sort_order)
        .options(
            selectinload(Franchise.games)
            .selectinload(Game.platforms)
            .selectinload(GamePlatform.platform),
            selectinload(Franchise.games).selectinload(Game.links),
        )
    )
    return [FranchiseOut.from_model(f) for f in session.scalars(query)]
