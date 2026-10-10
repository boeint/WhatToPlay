from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.lengths import LookupUnavailable, lookup_length

router = APIRouter(tags=["lengths"])


class LengthMatch(BaseModel):
    name: str
    year: int | None
    main_story: float | None   # hours, as HowLongToBeat has it
    hours: int | None          # rounded: what goes in the Length field
    players: int               # how many players submitted a main-story time
    url: str


class LengthLookup(BaseModel):
    matches: list[LengthMatch]


@router.get("/api/length-lookup", response_model=LengthLookup)
async def length_lookup(title: str = Query(min_length=1, max_length=255),
                        year: int | None = Query(None, ge=1950, le=2100)):
    """HowLongToBeat's closest matches for a title, best first (nothing is saved)."""
    try:
        return {"matches": await lookup_length(title, year)}
    except LookupUnavailable as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            f"HowLongToBeat couldn't be searched right now ({exc}). Try again later.") from None
