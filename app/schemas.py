"""Shapes of the data the API sends and receives (Pydantic models).

These are separate from the database tables in app/models.py: the API decides
what to expose, independently of how data is stored.
"""
import calendar
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import backloggd
from app.models import Franchise, Game, Status


def format_release(year: int | None, month: int | None, note: str | None) -> str:
    """Display label for a release date: "Aug 2007", "1998", "2025 (Early Access)", "TBA"."""
    parts = []
    if month and year:
        parts.append(f"{calendar.month_abbr[month]} {year}")
    elif year:
        parts.append(str(year))
    if note:
        parts.append(f"({note})" if parts else note)
    return " ".join(parts)


class PlatformOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # can be built from a database row

    id: int
    name: str


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    url: str


class GameOut(BaseModel):
    id: int
    title: str
    release_year: int | None
    release_month: int | None
    release_note: str | None
    released: str                  # read-only display label, built from the three fields above
    status: Status
    finished_on: date | None
    notes: str
    platforms: list[str]           # platform names, in the game's order
    links: list[LinkOut]
    backloggd_url: str | None      # manual override, or None
    backloggd_link: str            # read-only: the page to open (override or generated)

    @classmethod
    def from_model(cls, game: Game) -> "GameOut":
        return cls(
            id=game.id,
            title=game.title,
            release_year=game.release_year,
            release_month=game.release_month,
            release_note=game.release_note,
            released=format_release(game.release_year, game.release_month, game.release_note),
            status=game.status,
            finished_on=game.finished_on,
            notes=game.notes,
            platforms=[gp.platform.name for gp in game.platforms],
            links=[LinkOut.model_validate(link) for link in game.links],
            backloggd_url=game.backloggd_url,
            backloggd_link=backloggd.link(game.title, game.backloggd_url),
        )


class FranchiseOut(BaseModel):
    id: int
    name: str
    notes: str
    games: list[GameOut]           # in play order

    @classmethod
    def from_model(cls, franchise: Franchise) -> "FranchiseOut":
        return cls(
            id=franchise.id,
            name=franchise.name,
            notes=franchise.notes,
            games=[GameOut.from_model(g) for g in franchise.games],
        )


# --- Input (what the API accepts) -------------------------------------------
# str_strip_whitespace: " BioShock " is saved as "BioShock".

class FranchiseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    notes: str = ""


class FranchiseUpdate(BaseModel):
    """Every field is optional: send only what changes.

    Defaults are None so a field can be left out, but sending `"name": null`
    is rejected because the type is `str`.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(None, min_length=1, max_length=200)
    notes: str = None


def _check_url(value: str | None) -> str | None:
    if value is not None and not value.startswith(("http://", "https://")):
        raise ValueError("must start with http:// or https://")
    return value


class LinkIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2000)

    _url = field_validator("url")(_check_url)


class _GameRules(BaseModel):
    """Validation shared by GameCreate and GameUpdate."""
    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("release_note", "backloggd_url", mode="after", check_fields=False)
    @classmethod
    def empty_means_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("backloggd_url", mode="after", check_fields=False)
    @classmethod
    def url_scheme(cls, value: str | None) -> str | None:
        return _check_url(value)

    @field_validator("platforms", mode="after", check_fields=False)
    @classmethod
    def no_duplicate_platforms(cls, value: list[str]) -> list[str]:
        if len({p.lower() for p in value}) != len(value):
            raise ValueError("a platform is listed twice")
        return value


class GameCreate(_GameRules):
    title: str = Field(min_length=1, max_length=255)
    release_year: int | None = Field(None, ge=1950, le=2100)
    release_month: int | None = Field(None, ge=1, le=12)
    release_note: str | None = Field(None, max_length=50)
    status: Status = Status.UNPLAYED
    finished_on: date | None = None   # left out: set automatically when status is finished
    notes: str = ""
    platforms: list[str] = []         # platform names, in order
    links: list[LinkIn] = []
    backloggd_url: str | None = Field(None, max_length=500)


class GameUpdate(_GameRules):
    """Send only what changes. `platforms` and `links` replace the whole list.

    Fields that can be empty (release_month, finished_on, ...) accept null to
    clear them; the others reject null (see FranchiseUpdate).
    """
    franchise_id: int = None          # move the game to another franchise
    title: str = Field(None, min_length=1, max_length=255)
    release_year: int | None = Field(None, ge=1950, le=2100)
    release_month: int | None = Field(None, ge=1, le=12)
    release_note: str | None = Field(None, max_length=50)
    status: Status = None
    finished_on: date | None = None
    notes: str = None
    platforms: list[str] = None
    links: list[LinkIn] = None
    backloggd_url: str | None = Field(None, max_length=500)
