"""The WhatToPlay web app.

Run locally:
    uvicorn app.main:app --reload
then open http://localhost:8000/docs
"""
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Platform
from app.schemas import PlatformOut

app = FastAPI(title="WhatToPlay", version="0.1.0")

# "Give this endpoint a database session" — FastAPI calls get_session for us.
SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/api/platforms", response_model=list[PlatformOut])
def list_platforms(session: SessionDep):
    """All platforms, in display order."""
    return session.scalars(select(Platform).order_by(Platform.sort_order)).all()
