"""App preferences (Settings dialog), stored as key/value rows in the `settings` table.

A setting that was never saved has its default value.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Setting

DEFAULT_AI_INSTRUCTIONS = """\
How to add a franchise or games to my backlog:

- Research the franchise on the web (official sites, Wikipedia, Backloggd/IGDB). Include every game: mainline games and spin-offs. Minor ones are still added, as Skip with a note (see below).
- Put games in play order: release order, unless the story order is clearly better.
- Remakes and remasters are separate games, right after the original. If the remake is clearly the better way to play, mark the original Skip with the note "Play the remake instead".
- Release date: the full launch (month and year), never early access. If it isn't final, set TBA, with the expected year if one is announced.
- Platforms: everywhere the game is officially available, including later ports. If a retro game is playable through Nintendo Switch Online, also list NSO (Play on stays the original console).
- Play on: PC if the game is available on PC; otherwise the platform it originally came out on (e.g. SNES). Play on is always a platform, never a device: I play PC games on a Steam Deck and retro games on handhelds, and I note the device myself after playing.
- Minor games and games you decide to skip (mobile-only spin-offs, gacha games, compilations of games already listed, minor re-releases) are still added, with status Skip and a short note saying why.
- Length: the main-story time in hours, as on HowLongToBeat ("Main Story"), rounded to a whole hour. Leave it empty if there's no reliable figure.
- DLC and expansions are not separate games unless sold as standalone games.
- Check for duplicates first, including in other franchises.
- New games are Unplayed.
- Before adding or changing anything, show me the full list (title, release, platforms, play on, status, notes) and wait for my OK.
"""

# key -> (type, default)
DEFINITIONS: dict[str, tuple[type, object]] = {
    "ai_enabled": (bool, False),            # off by default: AI access is opt-in
    "ai_instructions": (str, DEFAULT_AI_INSTRUCTIONS),
}


def _decode(key: str, raw: str):
    kind, _ = DEFINITIONS[key]
    return raw == "true" if kind is bool else raw


def _encode(key: str, value) -> str:
    kind, _ = DEFINITIONS[key]
    return ("true" if value else "false") if kind is bool else str(value)


def all_preferences(session: Session) -> dict:
    stored = {s.key: s.value for s in session.scalars(select(Setting))}
    return {
        key: _decode(key, stored[key]) if key in stored else default
        for key, (_, default) in DEFINITIONS.items()
    }


def get_preference(session: Session, key: str):
    return all_preferences(session)[key]


def set_preferences(session: Session, changes: dict) -> None:
    for key, value in changes.items():
        row = session.get(Setting, key)
        if row is None:
            session.add(Setting(key=key, value=_encode(key, value)))
        else:
            row.value = _encode(key, value)
    session.commit()
