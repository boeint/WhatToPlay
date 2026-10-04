"""Export everything to a file, and import (replace everything) from one."""
import json
from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.deps import SessionDep
from app.models import Franchise, Game, Platform
from app.routers.franchises import WITH_GAMES
from app.routers.games import apply_fields, platforms_by_name
from app.schemas import ExportFile, ExportFranchise, GameCreate

router = APIRouter(tags=["backup"])

EXPORT_PREFIX = "whattoplay-export-"


def export_filename(day: date | None = None) -> str:
    return f"{EXPORT_PREFIX}{(day or date.today()).isoformat()}.json"


def build_export(session: Session) -> str:
    """All data as the text of a versioned export file (used by Export and the daily backup)."""
    platforms = session.scalars(select(Platform.name).order_by(Platform.sort_order)).all()
    franchises = session.scalars(
        select(Franchise).order_by(Franchise.sort_order).options(*WITH_GAMES)
    )
    export = ExportFile(
        format="whattoplay-export",
        version=1,
        exported_at=datetime.now(UTC).replace(microsecond=0),
        platforms=platforms,
        franchises=[
            ExportFranchise(
                name=f.name,
                notes=f.notes,
                games=[GameCreate.from_model(g) for g in f.games],
            )
            for f in franchises
        ],
    )
    return json.dumps(export.model_dump(mode="json"), indent=2, ensure_ascii=False)


@router.get("/api/export")
def export_all(session: SessionDep):
    """Download all data as a versioned JSON file."""
    return Response(
        build_export(session),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{export_filename()}"'},
    )


def require_replace(replace: bool) -> None:
    """Safety latch shared by import and restore."""
    if not replace:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "This replaces all existing data. Add ?replace=true to confirm.",
        )


@router.post("/api/import")
def import_all(data: ExportFile, session: SessionDep, replace: bool = False):
    """Replace ALL franchises, games and platforms with the contents of an export file.

    The whole file is validated before anything changes, and the replacement runs
    as a single transaction: it either fully succeeds or changes nothing.
    Requires `?replace=true` as a safety latch.
    """
    require_replace(replace)
    return replace_all(session, data)


def replace_all(session: Session, data: ExportFile) -> dict:
    """Replace everything with a validated export, in one transaction. Returns the new counts."""
    # 1. Remove all franchises (the database cascades to games, platforms rows, links).
    session.execute(delete(Franchise))

    # 2. Make the platform list exactly the file's list, in the file's order.
    existing = platforms_by_name(session)
    wanted = {name.lower() for name in data.platforms}
    for key, platform in existing.items():
        if key not in wanted:
            session.delete(platform)
    for position, name in enumerate(data.platforms, start=1):
        platform = existing.get(name.lower()) or Platform(name=name)
        platform.name, platform.sort_order = name, position
        session.add(platform)
    session.flush()
    known = platforms_by_name(session)

    # 3. Add franchises and games in file order.
    for f_pos, f in enumerate(data.franchises, start=1):
        franchise = Franchise(name=f.name, notes=f.notes, sort_order=f_pos)
        for g_pos, g in enumerate(f.games, start=1):
            game = Game(sort_order=g_pos)
            # model_dump() without exclude_unset: finished_on always counts as given,
            # so a restored finished game without a date is not stamped with today.
            apply_fields(session, game, g.model_dump(), known)
            franchise.games.append(game)
        session.add(franchise)

    session.commit()
    return {
        "franchises": session.scalar(select(func.count()).select_from(Franchise)),
        "games": session.scalar(select(func.count()).select_from(Game)),
        "platforms": session.scalar(select(func.count()).select_from(Platform)),
    }
