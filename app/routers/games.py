from datetime import date

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.deps import SessionDep
from app.models import Franchise, Game, GameLink, GamePlatform, Platform, Status
from app.schemas import GameCreate, GameOut, GameUpdate

router = APIRouter(tags=["games"])

WITH_DETAILS = (
    selectinload(Game.platforms).selectinload(GamePlatform.platform),
    selectinload(Game.links),
)


def invalid(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def get_game_or_404(session: Session, game_id: int) -> Game:
    game = session.scalar(select(Game).where(Game.id == game_id).options(*WITH_DETAILS))
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Game {game_id} not found")
    return game


def next_sort_order(session: Session, franchise_id: int) -> int:
    """Position after the last game of a franchise."""
    last = session.scalar(
        select(func.max(Game.sort_order)).where(Game.franchise_id == franchise_id)
    )
    return (last or 0) + 1


def platform_rows(session: Session, names: list[str]) -> list[GamePlatform]:
    """Turn platform names into game_platforms rows, keeping the given order."""
    found = {
        p.name.lower(): p
        for p in session.scalars(select(Platform).where(Platform.name.in_(names)))
    }
    unknown = [n for n in names if n.lower() not in found]
    if unknown:
        raise invalid(f"Unknown platform: {', '.join(unknown)}")
    return [
        GamePlatform(platform=found[n.lower()], sort_order=i)
        for i, n in enumerate(names, start=1)
    ]


def apply_fields(session: Session, game: Game, fields: dict) -> None:
    """Copy validated input onto a game (used by create and update)."""
    old_status = game.status
    date_sent = "finished_on" in fields

    if "platforms" in fields:
        game.platforms = platform_rows(session, fields.pop("platforms"))
    if "links" in fields:
        game.links = [
            GameLink(label=link["label"], url=link["url"], sort_order=i)
            for i, link in enumerate(fields.pop("links"), start=1)
        ]
    for name, value in fields.items():
        setattr(game, name, value)

    # Release date: a month only makes sense with a year.
    if game.release_month is not None and game.release_year is None:
        raise invalid("release_month needs a release_year")

    # finished_on: today when a game *becomes* finished (unless a date was given),
    # editable while finished, cleared when it stops being finished.
    if game.status != Status.FINISHED:
        if date_sent and game.finished_on is not None:
            raise invalid("finished_on can only be set on a finished game")
        game.finished_on = None
    elif old_status != Status.FINISHED and not date_sent and game.finished_on is None:
        game.finished_on = date.today()


@router.post(
    "/api/franchises/{franchise_id}/games",
    response_model=GameOut,
    status_code=status.HTTP_201_CREATED,
)
def create_game(franchise_id: int, data: GameCreate, session: SessionDep):
    """Add a game at the end of a franchise."""
    if session.get(Franchise, franchise_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Franchise {franchise_id} not found")
    game = Game(franchise_id=franchise_id, sort_order=next_sort_order(session, franchise_id))
    # exclude_unset: fields left out use the database defaults, and a missing
    # finished_on is not mistaken for "explicitly cleared".
    apply_fields(session, game, data.model_dump(exclude_unset=True))
    session.add(game)
    session.commit()
    return GameOut.from_model(get_game_or_404(session, game.id))


@router.get("/api/games/{game_id}", response_model=GameOut)
def get_game(game_id: int, session: SessionDep):
    """One game."""
    return GameOut.from_model(get_game_or_404(session, game_id))


@router.patch("/api/games/{game_id}", response_model=GameOut)
def update_game(game_id: int, data: GameUpdate, session: SessionDep):
    """Change a game. Only the fields sent are changed.

    Sending `franchise_id` moves the game to the end of that franchise.
    """
    game = get_game_or_404(session, game_id)
    changes = data.model_dump(exclude_unset=True)

    new_franchise = changes.pop("franchise_id", game.franchise_id)
    if new_franchise != game.franchise_id:
        if session.get(Franchise, new_franchise) is None:
            raise invalid(f"Franchise {new_franchise} not found")
        game.franchise_id = new_franchise
        game.sort_order = next_sort_order(session, new_franchise)

    apply_fields(session, game, changes)
    session.commit()
    return GameOut.from_model(get_game_or_404(session, game_id))


@router.delete("/api/games/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: int, session: SessionDep):
    """Delete a game."""
    session.delete(get_game_or_404(session, game_id))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
