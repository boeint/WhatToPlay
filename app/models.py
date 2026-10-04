"""Database tables, described as Python classes (SQLAlchemy ORM).

Each class is one table; each `Mapped[...]` attribute is one column.
`Mapped[int | None]` means the column may be empty (NULL).
The table design is documented in PLAN.md.
"""
import enum
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Status(str, enum.Enum):
    UNPLAYED = "unplayed"
    PLAYING = "playing"
    FINISHED = "finished"
    SKIP = "skip"


class Timestamps:
    """Adds created_at / updated_at columns, filled in automatically."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    sort_order: Mapped[int]


class Franchise(Timestamps, Base):
    __tablename__ = "franchises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int]

    games: Mapped[list["Game"]] = relationship(
        back_populates="franchise",
        order_by="Game.sort_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Game(Timestamps, Base):
    __tablename__ = "games"
    __table_args__ = (
        CheckConstraint("release_month BETWEEN 1 AND 12", name="release_month_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    franchise_id: Mapped[int] = mapped_column(
        ForeignKey("franchises.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    release_year: Mapped[int | None] = mapped_column(SmallInteger)
    release_month: Mapped[int | None] = mapped_column(SmallInteger)
    release_note: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[Status] = mapped_column(
        Enum(Status, name="game_status", values_callable=lambda e: [s.value for s in e]),
        default=Status.UNPLAYED,
        server_default=Status.UNPLAYED.value,
    )
    finished_on: Mapped[date | None]
    notes: Mapped[str] = mapped_column(Text, default="")
    backloggd_url: Mapped[str | None] = mapped_column(String(500))  # None = generated from title
    sort_order: Mapped[int]

    franchise: Mapped[Franchise] = relationship(back_populates="games")
    platforms: Mapped[list["GamePlatform"]] = relationship(
        order_by="GamePlatform.sort_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    links: Mapped[list["GameLink"]] = relationship(
        order_by="GameLink.sort_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GamePlatform(Base):
    """Links a game to one of its platforms. A game has one row per platform."""
    __tablename__ = "game_platforms"

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    # No cascade here: a platform that is still used by a game cannot be deleted.
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id"), primary_key=True
    )
    sort_order: Mapped[int]

    platform: Mapped[Platform] = relationship()


class GameLink(Base):
    __tablename__ = "game_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2000))
    sort_order: Mapped[int]
