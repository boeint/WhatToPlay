"""Database foundations shared by the whole app."""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

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
