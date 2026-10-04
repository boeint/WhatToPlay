"""Add a few sample franchises to an EMPTY database, for development.

Run from the project folder:
    python -m scripts.sample_data
Refuses to run if the database already contains franchises.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import Franchise, Game, GameLink, GamePlatform, Platform, Status

# (franchise name, notes, [(title, year, month, tba, status, finished_on, platforms, notes, backloggd override)])
SAMPLE = [
    ("BioShock", "", [
        ("BioShock", 2007, 8, False, Status.FINISHED, date(2024, 3, 2), ["PC", "PS4"], "", None),
        ("BioShock 2", 2010, 2, False, Status.PLAYING, None, ["PC"], "", None),
        ("BioShock Infinite", 2013, 3, False, Status.UNPLAYED, None, ["PC", "Switch"], "", None),
    ]),
    ("Pokémon", "Mainline generations only.", [
        ("Pokémon Red / Blue", 1996, 2, False, Status.UNPLAYED, None, ["Game Boy"], "", None),
        ("Pokémon Legends: Z-A", 2025, None, True, Status.SKIP, None, ["Switch", "Switch 2"], "", None),
    ]),
    ("Alan Wake", "", [
        ("Alan Wake's American Nightmare", 2012, 2, False, Status.UNPLAYED, None, ["PC", "Xbox 360"], "",
         "https://backloggd.com/games/alan-wake-s-american-nightmare/"),
        ("Hades II", None, None, True, Status.UNPLAYED, None, ["PC"], "Wrong franchise on purpose", None),
    ]),
]


def main() -> None:
    with Session(get_engine()) as session:
        if session.scalar(select(func.count()).select_from(Franchise)):
            raise SystemExit("Database already has franchises: not adding sample data.")

        platforms = {p.name: p for p in session.scalars(select(Platform))}
        for f_order, (name, notes, games) in enumerate(SAMPLE, start=1):
            franchise = Franchise(name=name, notes=notes, sort_order=f_order)
            for g_order, (title, year, month, tba, status, finished, plats, g_notes, bl) in enumerate(games, start=1):
                game = Game(
                    title=title, release_year=year, release_month=month, release_tba=tba,
                    status=status, finished_on=finished, notes=g_notes, backloggd_url=bl,
                    sort_order=g_order,
                    platforms=[GamePlatform(platform=platforms[p], sort_order=i)
                               for i, p in enumerate(plats, start=1)],
                )
                franchise.games.append(game)
            if name == "BioShock":
                franchise.games[0].links.append(
                    GameLink(label="review", url="https://example.com/review", sort_order=1)
                )
            session.add(franchise)

        session.commit()
        print(f"Added {len(SAMPLE)} franchises.")


if __name__ == "__main__":
    main()
