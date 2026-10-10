"""Game lengths from HowLongToBeat ("Main Story").

HowLongToBeat has no official API: this uses the unofficial howlongtobeatpy package,
which searches the site the way its own search page does. If HowLongToBeat changes
its site, lookups fail until the package catches up; lengths can still be typed by hand.
"""
import re

from howlongtobeatpy import HowLongToBeat


class LookupUnavailable(Exception):
    """HowLongToBeat couldn't be searched (site down, changed, or rate-limiting)."""


def search_text(title: str) -> str:
    """The title as HowLongToBeat knows it: brackets name the edition played
    ("Crash Bandicoot (N. Sane Trilogy)"), not the game, so they're left out."""
    return re.sub(r"\s*\(.*?\)", "", title).strip() or title


def whole_hours(main_story: float) -> int | None:
    """Rounded to the nearest hour (half up), at least 1; None when there's no figure."""
    return max(1, int(main_story + 0.5)) if main_story else None


async def lookup_length(title: str, year: int | None = None, limit: int = 5) -> list[dict]:
    """HowLongToBeat's closest matches for a game, best first.

    Ranked by how closely the name matches, then by release year, then by how many
    players submitted a time. Raises LookupUnavailable if the site can't be searched.
    """
    try:
        results = await HowLongToBeat().async_search(search_text(title))
    except Exception as exc:   # the package's own errors vary by version
        raise LookupUnavailable(str(exc)) from exc
    if results is None:        # the package's way of saying the request failed
        raise LookupUnavailable("HowLongToBeat didn't answer")

    def rank(entry):
        players = entry.json_content.get("comp_main_count") or 0
        return (round(entry.similarity, 1), year is not None and entry.release_world == year, players)

    return [
        {
            "name": e.game_name,
            "year": e.release_world or None,
            "main_story": round(e.main_story, 1) if e.main_story else None,
            "hours": whole_hours(e.main_story),
            "players": e.json_content.get("comp_main_count") or 0,
            "url": f"https://howlongtobeat.com/game/{e.game_id}",
        }
        for e in sorted(results, key=rank, reverse=True)[:limit]
    ]
