"""Shared test setup.

The tests run against a real MariaDB database, because several rules live in the
database itself (accent-insensitive names, allowed statuses, cascading deletes).
They empty that database all the time, so its name MUST end in "_test":
  - locally: the .env settings, with the database switched to whattoplay_test
    (or TEST_DB_NAME);
  - on GitHub: a throwaway MariaDB started for the run.
"""
import os

# Before anything reads the app's settings: use the test database, and keep the
# daily-backup task off unless a test turns it on.
os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "whattoplay_test")
os.environ["BACKUP_DIR"] = os.path.join(os.path.dirname(__file__), "_no_backups_here")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, text

from app.config import get_settings
from app.db import get_engine

ROOT = os.path.dirname(os.path.dirname(__file__))

if not get_settings().db_name.endswith("_test"):
    pytest.exit(f"Refusing to run: database '{get_settings().db_name}' doesn't end in '_test'.", returncode=2)


@pytest.fixture(scope="session")
def initial_platforms():
    """Build the test database from scratch (all migrations); return the starting platforms."""
    engine = get_engine()
    existing = MetaData()
    existing.reflect(bind=engine)
    existing.drop_all(bind=engine)                     # everything, including alembic_version
    command.upgrade(Config(os.path.join(ROOT, "alembic.ini")), "head")
    with engine.connect() as conn:
        return conn.execute(text("SELECT id, name, sort_order FROM platforms ORDER BY sort_order")).all()


@pytest.fixture(autouse=True)
def clean_database(initial_platforms):
    """Every test starts with no franchises or settings and the original platform list."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM franchises"))   # cascades to games, their platforms and links
        conn.execute(text("DELETE FROM settings"))
        ids = [p.id for p in initial_platforms]
        conn.execute(text(f"DELETE FROM platforms WHERE id NOT IN ({','.join(map(str, ids))})"))
        for p in initial_platforms:
            conn.execute(
                text("INSERT INTO platforms (id, name, sort_order) VALUES (:id, :name, :sort_order) "
                     "ON DUPLICATE KEY UPDATE name = VALUES(name), sort_order = VALUES(sort_order)"),
                p._asdict(),
            )
    yield


@pytest.fixture(scope="session")
def client(initial_platforms):
    """The app, called directly (no server); its start-up runs once for the whole session."""
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_franchise(client):
    """make_franchise("Name", [{"title": ...}, ...]) -> the created franchise (as the API returns it)."""
    def make(name="Test Franchise", games=(), notes=""):
        response = client.post("/api/franchises", json={"name": name, "notes": notes, "games": list(games)})
        assert response.status_code == 201, response.text
        return response.json()
    return make


def detail(response) -> str:
    """The error message of a refused request, as one string."""
    body = response.json()["detail"]
    return body if isinstance(body, str) else "; ".join(e["msg"] for e in body)
