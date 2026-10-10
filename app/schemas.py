"""Shapes of the data the API sends and receives (Pydantic models).

These are separate from the database tables in app/models.py: the API decides
what to expose, independently of how data is stored.
"""
import calendar
import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app import backloggd
from app.models import Franchise, Game, Status


def name_key(name: str) -> str:
    """Compare names the way the database does: ignoring case and accents.

    The database collation (utf8mb4_unicode_ci) treats "Pokemon" and "Pokémon" as equal.
    """
    decomposed = unicodedata.normalize("NFKD", name.strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def format_release(year: int | None, month: int | None, tba: bool) -> str:
    """Display label for a release date: "Aug 2007", "1998", "2026 (TBA)", "TBA"."""
    if month and year:
        label = f"{calendar.month_abbr[month]} {year}"
    elif year:
        label = str(year)
    else:
        label = ""
    if tba:
        return f"{label} (TBA)" if label else "TBA"
    return label


class PlatformOut(BaseModel):
    id: int
    name: str
    used_by: int = 0                  # number of games listing this platform


class PlatformIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=50)


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
    release_tba: bool              # release date not final; a year, if set, is the expected one
    released: str                  # read-only display label, built from the three fields above
    status: Status
    finished_on: date | None
    length_hours: int | None       # main story, in hours
    notes: str
    platforms: list[str]           # platform names, in the game's order
    play_on: str | None            # where the user will play it: one of `platforms`
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
            release_tba=game.release_tba,
            released=format_release(game.release_year, game.release_month, game.release_tba),
            status=game.status,
            finished_on=game.finished_on,
            length_hours=game.length_hours,
            notes=game.notes,
            platforms=[gp.platform.name for gp in game.platforms],
            play_on=game.play_on.name if game.play_on else None,
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
# extra="forbid": an unknown field (e.g. a typo like "relase_year") is an error,
# not silently ignored.

class FranchiseCreate(BaseModel):
    """A new franchise, optionally with its games (created together, all or nothing)."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    notes: str = ""
    games: list["GameCreate"] = []    # in play order


class FranchiseUpdate(BaseModel):
    """Every field is optional: send only what changes.

    Defaults are None so a field can be left out, but sending `"name": null`
    is rejected because the type is `str`.
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(None, min_length=1, max_length=200)
    notes: str = None


def _check_url(value: str | None) -> str | None:
    if value is not None and not value.startswith(("http://", "https://")):
        raise ValueError("must start with http:// or https://")
    return value


class LinkIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    label: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2000)

    _url = field_validator("url")(_check_url)


class _GameRules(BaseModel):
    """Validation shared by GameCreate and GameUpdate."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("backloggd_url", mode="after", check_fields=False)
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
        if len({name_key(p) for p in value}) != len(value):
            raise ValueError("a platform is listed twice")
        return value


class GameCreate(_GameRules):
    title: str = Field(min_length=1, max_length=255)
    release_year: int | None = Field(None, ge=1950, le=2100)
    release_month: int | None = Field(None, ge=1, le=12)
    release_tba: bool = False
    status: Status = Status.UNPLAYED
    finished_on: date | None = None   # left out: set automatically when status is finished
    length_hours: int | None = Field(None, ge=1, le=999)   # main story, in hours
    notes: str = ""
    platforms: list[str] = []         # platform names, in order
    play_on: str | None = None        # one of `platforms`
    links: list[LinkIn] = []
    backloggd_url: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def consistent(self) -> "GameCreate":
        if self.release_month is not None and self.release_year is None:
            raise ValueError("release_month needs a release_year")
        if self.play_on is not None and name_key(self.play_on) not in {name_key(p) for p in self.platforms}:
            raise ValueError("play_on must be one of the game's platforms")
        if self.finished_on is not None and self.status != Status.FINISHED:
            raise ValueError("finished_on can only be set on a finished game")
        return self

    @classmethod
    def from_model(cls, game: Game) -> "GameCreate":
        """A stored game as input data (used by export)."""
        return cls(
            title=game.title,
            release_year=game.release_year,
            release_month=game.release_month,
            release_tba=game.release_tba,
            status=game.status,
            finished_on=game.finished_on,
            length_hours=game.length_hours,
            notes=game.notes,
            platforms=[gp.platform.name for gp in game.platforms],
            play_on=game.play_on.name if game.play_on else None,
            links=[LinkIn(label=link.label, url=link.url) for link in game.links],
            backloggd_url=game.backloggd_url,
        )


class GameUpdate(_GameRules):
    """Send only what changes. `platforms` and `links` replace the whole list.

    Fields that can be empty (release_month, finished_on, ...) accept null to
    clear them; the others reject null (see FranchiseUpdate).
    """
    franchise_id: int = None          # move the game to another franchise
    title: str = Field(None, min_length=1, max_length=255)
    release_year: int | None = Field(None, ge=1950, le=2100)
    release_month: int | None = Field(None, ge=1, le=12)
    release_tba: bool = None
    status: Status = None
    finished_on: date | None = None
    length_hours: int | None = Field(None, ge=1, le=999)
    notes: str = None
    platforms: list[str] = None
    play_on: str | None = None        # null clears it
    links: list[LinkIn] = None
    backloggd_url: str | None = Field(None, max_length=500)


# --- Export / import file ------------------------------------------------------
# Versioned, no database ids: order is the order of the lists, and platforms and
# franchises are referred to by name, so a file can be imported into any install.

class ExportFranchise(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    notes: str = ""
    games: list[GameCreate] = []      # in play order


class ExportFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["whattoplay-export"]
    version: Literal[1]
    exported_at: datetime | None = None
    platforms: list[str]              # every platform, in display order
    franchises: list[ExportFranchise] # in custom order

    @model_validator(mode="after")
    def consistent(self) -> "ExportFile":
        if any(not p.strip() or len(p) > 50 for p in self.platforms):
            raise ValueError("platform names must be 1-50 characters")
        if len({name_key(p) for p in self.platforms}) != len(self.platforms):
            raise ValueError("a platform is listed twice in 'platforms'")
        seen: dict[str, str] = {}
        for franchise in self.franchises:
            key = name_key(franchise.name)
            if key in seen:
                raise ValueError(
                    f"franchise names '{seen[key]}' and '{franchise.name}' count as the same "
                    "(names are compared ignoring case and accents)"
                )
            seen[key] = franchise.name
        known = {name_key(p) for p in self.platforms}
        for fi, franchise in enumerate(self.franchises):
            for gi, game in enumerate(franchise.games):
                unknown = [p for p in game.platforms if name_key(p) not in known]
                if unknown:
                    raise ValueError(
                        f"franchises.{fi}.games.{gi} ('{game.title}'): "
                        f"platform not in 'platforms': {', '.join(unknown)}"
                    )
        return self


# FranchiseCreate refers to GameCreate, which is defined after it.
FranchiseCreate.model_rebuild()
