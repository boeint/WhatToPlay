from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.deps import SessionDep
from app.models import Franchise, Game, GamePlatform
from app.routers.games import apply_fields, platforms_by_name
from app.schemas import FranchiseCreate, FranchiseOut, FranchiseUpdate

router = APIRouter(tags=["franchises"])

# Load each franchise's games, their platforms and links in a few bulk queries
# instead of one query per franchise and per game.
WITH_GAMES = (
    selectinload(Franchise.games)
    .selectinload(Game.platforms)
    .selectinload(GamePlatform.platform),
    selectinload(Franchise.games).selectinload(Game.links),
)


def get_franchise_or_404(session: Session, franchise_id: int) -> Franchise:
    franchise = session.scalar(
        select(Franchise).where(Franchise.id == franchise_id).options(*WITH_GAMES)
    )
    if franchise is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Franchise {franchise_id} not found")
    return franchise


def check_name_free(session: Session, name: str, except_id: int | None = None) -> None:
    """409 Conflict if another franchise already has this name (case-insensitive)."""
    query = select(Franchise.id).where(Franchise.name == name)
    if except_id is not None:
        query = query.where(Franchise.id != except_id)
    if session.scalar(query) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A franchise named '{name}' already exists")


def check_same_ids(sent: list[int], expected: set[int], what: str) -> None:
    """A new order must list every existing item exactly once."""
    if len(sent) != len(set(sent)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"An id appears twice in the {what} order")
    missing, unknown = expected - set(sent), set(sent) - expected
    if missing or unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"The {what} order must list every {what} exactly once "
            f"(missing: {sorted(missing) or 'none'}, unknown: {sorted(unknown) or 'none'})",
        )


@router.get("/api/franchises", response_model=list[FranchiseOut])
def list_franchises(session: SessionDep):
    """All franchises in order, each with its games in play order."""
    query = select(Franchise).order_by(Franchise.sort_order).options(*WITH_GAMES)
    return [FranchiseOut.from_model(f) for f in session.scalars(query)]


@router.get("/api/franchises/{franchise_id}", response_model=FranchiseOut)
def get_franchise(franchise_id: int, session: SessionDep):
    """One franchise with its games."""
    return FranchiseOut.from_model(get_franchise_or_404(session, franchise_id))


@router.post("/api/franchises", response_model=FranchiseOut, status_code=status.HTTP_201_CREATED)
def create_franchise(data: FranchiseCreate, session: SessionDep):
    """Add a franchise at the end of the list, optionally with its games.

    Everything is created in one transaction: if one game is invalid, nothing is created.
    """
    check_name_free(session, data.name)
    last = session.scalar(select(func.max(Franchise.sort_order))) or 0
    franchise = Franchise(name=data.name, notes=data.notes, sort_order=last + 1)
    known = platforms_by_name(session) if data.games else None
    for position, game_data in enumerate(data.games, start=1):
        game = Game(sort_order=position)
        apply_fields(session, game, game_data.model_dump(exclude_unset=True), known)
        franchise.games.append(game)
    session.add(franchise)
    session.commit()
    return FranchiseOut.from_model(get_franchise_or_404(session, franchise.id))


@router.patch("/api/franchises/{franchise_id}", response_model=FranchiseOut)
def update_franchise(franchise_id: int, data: FranchiseUpdate, session: SessionDep):
    """Change a franchise's name and/or notes. Only the fields sent are changed."""
    franchise = get_franchise_or_404(session, franchise_id)
    changes = data.model_dump(exclude_unset=True)  # only fields present in the request
    if "name" in changes:
        check_name_free(session, changes["name"], except_id=franchise_id)
    for field, value in changes.items():
        setattr(franchise, field, value)
    session.commit()
    return FranchiseOut.from_model(get_franchise_or_404(session, franchise_id))


@router.delete("/api/franchises/{franchise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_franchise(franchise_id: int, session: SessionDep):
    """Delete a franchise and all its games."""
    franchise = get_franchise_or_404(session, franchise_id)
    session.delete(franchise)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/api/franchise-order", status_code=status.HTTP_204_NO_CONTENT)
def set_franchise_order(franchise_ids: list[int], session: SessionDep):
    """Save the custom franchise order: every franchise id, in the new order."""
    franchises = {f.id: f for f in session.scalars(select(Franchise))}
    check_same_ids(franchise_ids, set(franchises), "franchise")
    for position, franchise_id in enumerate(franchise_ids, start=1):
        franchises[franchise_id].sort_order = position
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/api/franchises/{franchise_id}/game-order", response_model=FranchiseOut)
def set_game_order(franchise_id: int, game_ids: list[int], session: SessionDep):
    """Save a franchise's play order: every game id of that franchise, in the new order."""
    franchise = get_franchise_or_404(session, franchise_id)
    games = {g.id: g for g in franchise.games}
    check_same_ids(game_ids, set(games), "game")
    for position, game_id in enumerate(game_ids, start=1):
        games[game_id].sort_order = position
    session.commit()
    return FranchiseOut.from_model(get_franchise_or_404(session, franchise_id))
