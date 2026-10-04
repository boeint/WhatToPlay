"""Shapes of the data the API sends and receives (Pydantic models).

These are separate from the database tables in app/models.py: the API decides
what to expose, independently of how data is stored.
"""
from pydantic import BaseModel, ConfigDict


class PlatformOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # can be built from a database row

    id: int
    name: str
