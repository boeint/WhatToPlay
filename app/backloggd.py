"""Everything specific to Backloggd (https://backloggd.com) lives here.

Backloggd is the current source of each game's external page. Keeping it in one
module means another provider (or RomM) can replace it later without touching
the rest of the app.
"""
import re
import unicodedata

BASE_URL = "https://backloggd.com/games/"


def slug(title: str) -> str:
    """Best-guess Backloggd slug for a title (ported from the legacy app).

    "Pokémon Red / Blue" -> "pokemon-red", "GTA III" -> "grand-theft-auto-iii"
    """
    s = title.split(" / ")[0]                       # "Red / Blue" pairs: first variant
    s = re.sub(r"\bGTA\b", "Grand Theft Auto", s)   # expand abbreviation
    s = re.sub(r"\([^)]*\)", " ", s)                # drop "(1996)", "(Remake)", ...
    s = unicodedata.normalize("NFD", s)             # strip accents: é -> e
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("'", "").replace("’", "")  # drop apostrophes
    s = s.replace("&", " ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def link(title: str, override: str | None) -> str:
    """The page to open for a game: the saved override wins, else the generated one."""
    return override or f"{BASE_URL}{slug(title)}/"
