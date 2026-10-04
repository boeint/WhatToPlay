"""Database foundations shared by the whole app."""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import get_settings

# Predictable names for indexes, keys and constraints (e.g. "fk_games_franchise_id_franchises").
# Alembic needs stable names to change or drop them in later migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Parent class of every table in app/models.py."""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@lru_cache
def get_engine() -> Engine:
    """The connection pool to the database, created once on first use."""
    # pool_pre_ping: check a pooled connection is still alive before using it
    # (MariaDB closes idle connections after a while).
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """One database session per API request, closed when the request ends."""
    with Session(get_engine()) as session:
        yield session
