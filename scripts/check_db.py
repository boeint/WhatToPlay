"""Check that the app can reach its database with the current settings.

Run from the project folder:
    python -m scripts.check_db
"""
from sqlalchemy import create_engine, text

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"Connecting to {settings.db_host}:{settings.db_port} "
          f"as '{settings.db_user}', database '{settings.db_name}'...")

    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        version, database, user = conn.execute(
            text("SELECT VERSION(), DATABASE(), CURRENT_USER()")
        ).one()
        tables = conn.execute(text("SHOW TABLES")).scalars().all()

    print("OK")
    print(f"  Server version : {version}")
    print(f"  Database       : {database}")
    print(f"  Logged in as   : {user}")
    print(f"  Tables         : {', '.join(tables) if tables else '(none yet)'}")


if __name__ == "__main__":
    main()
