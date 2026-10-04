from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.deps import SessionDep
from app.models import Franchise, Game, GamePlatform
from app.schemas import FranchiseCreate, FranchiseOut, FranchiseUpdate

router = APIRouter(prefix="/api/franchises", tags=["franchises"])

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


@router.get("", response_model=list[FranchiseOut])
def list_franchises(session: SessionDep):
    """All franchises in order, each with its games in play order."""
    query = select(Franchise).order_by(Franchise.sort_order).options(*WITH_GAMES)
    return [FranchiseOut.from_model(f) for f in session.scalars(query)]


@router.get("/{franchise_id}", response_model=FranchiseOut)
def get_franchise(franchise_id: int, session: SessionDep):
    """One franchise with its games."""
    return FranchiseOut.from_model(get_franchise_or_404(session, franchise_id))


@router.post("", response_model=FranchiseOut, status_code=status.HTTP_201_CREATED)
def create_franchise(data: FranchiseCreate, session: SessionDep):
    """Add a franchise at the end of the list."""
    check_name_free(session, data.name)
    last = session.scalar(select(func.max(Franchise.sort_order))) or 0
    franchise = Franchise(name=data.name, notes=data.notes, sort_order=last + 1)
    session.add(franchise)
    session.commit()
    return FranchiseOut.from_model(get_franchise_or_404(session, franchise.id))


@router.patch("/{franchise_id}", response_model=FranchiseOut)
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


@router.delete("/{franchise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_franchise(franchise_id: int, session: SessionDep):
    """Delete a franchise and all its games."""
    franchise = get_franchise_or_404(session, franchise_id)
    session.delete(franchise)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
