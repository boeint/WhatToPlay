"""Shared dependencies for API endpoints."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_session

# "Give this endpoint a database session" — FastAPI calls get_session for us
# and closes the session when the request ends.
SessionDep = Annotated[Session, Depends(get_session)]
