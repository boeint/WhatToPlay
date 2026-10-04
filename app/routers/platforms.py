from fastapi import APIRouter
from sqlalchemy import select

from app.deps import SessionDep
from app.models import Platform
from app.schemas import PlatformOut

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformOut])
def list_platforms(session: SessionDep):
    """All platforms, in display order."""
    return session.scalars(select(Platform).order_by(Platform.sort_order)).all()
