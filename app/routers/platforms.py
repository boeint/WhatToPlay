from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import SessionDep
from app.models import GamePlatform, Platform
from app.routers.franchises import check_same_ids
from app.schemas import PlatformIn, PlatformOut, name_key

router = APIRouter(tags=["platforms"])


def usage(session: Session) -> dict[int, int]:
    """Number of games listing each platform."""
    rows = session.execute(
        select(GamePlatform.platform_id, func.count()).group_by(GamePlatform.platform_id)
    )
    return dict(rows.all())


def to_out(platform: Platform, used: dict[int, int]) -> PlatformOut:
    return PlatformOut(id=platform.id, name=platform.name, used_by=used.get(platform.id, 0))


def get_platform_or_404(session: Session, platform_id: int) -> Platform:
    platform = session.get(Platform, platform_id)
    if platform is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Platform {platform_id} not found")
    return platform


def check_name_free(session: Session, name: str, except_id: int | None = None) -> None:
    """409 Conflict if another platform has this name (ignoring case and accents)."""
    for other in session.scalars(select(Platform)):
        if other.id != except_id and name_key(other.name) == name_key(name):
            raise HTTPException(status.HTTP_409_CONFLICT, f"A platform named '{other.name}' already exists")


@router.get("/api/platforms", response_model=list[PlatformOut])
def list_platforms(session: SessionDep):
    """All platforms, in display order, with how many games use each."""
    used = usage(session)
    return [to_out(p, used) for p in session.scalars(select(Platform).order_by(Platform.sort_order))]


@router.post("/api/platforms", response_model=PlatformOut, status_code=status.HTTP_201_CREATED)
def create_platform(data: PlatformIn, session: SessionDep):
    """Add a platform at the end of the list."""
    check_name_free(session, data.name)
    last = session.scalar(select(func.max(Platform.sort_order))) or 0
    platform = Platform(name=data.name, sort_order=last + 1)
    session.add(platform)
    session.commit()
    return to_out(platform, {})


@router.patch("/api/platforms/{platform_id}", response_model=PlatformOut)
def rename_platform(platform_id: int, data: PlatformIn, session: SessionDep):
    """Rename a platform; games using it show the new name."""
    platform = get_platform_or_404(session, platform_id)
    check_name_free(session, data.name, except_id=platform_id)
    platform.name = data.name
    session.commit()
    return to_out(platform, usage(session))


@router.delete("/api/platforms/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform(platform_id: int, session: SessionDep):
    """Delete a platform no game uses (refused otherwise, so nothing is lost)."""
    platform = get_platform_or_404(session, platform_id)
    used = usage(session).get(platform_id, 0)
    if used:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"'{platform.name}' is used by {used} game{'s' if used != 1 else ''}: remove it from them first",
        )
    session.delete(platform)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/api/platform-order", status_code=status.HTTP_204_NO_CONTENT)
def set_platform_order(platform_ids: list[int], session: SessionDep):
    """Save the platform display order: every platform id, in the new order."""
    platforms = {p.id: p for p in session.scalars(select(Platform))}
    check_same_ids(platform_ids, set(platforms), "platform")
    for position, platform_id in enumerate(platform_ids, start=1):
        platforms[platform_id].sort_order = position
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
