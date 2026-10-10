"""MCP server: lets an AI assistant (Claude Code) read the backlog and add games.

Mounted at /mcp by app/main.py. Every request is refused unless the AI assistant
switch is on in Settings. The tools reuse the app's own logic and validation, so
the assistant can't do anything the app itself wouldn't allow.
"""
import anyio
from fastapi import HTTPException
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.db import get_engine
from app.models import Franchise, Game, Platform, Status
from app.preferences import get_preference
from app.routers.franchises import WITH_GAMES, create_franchise
from app.routers.games import apply_fields, next_sort_order, platforms_by_name, update_game as update_game_endpoint
from app.schemas import FranchiseCreate, FranchiseOut, GameCreate, GameOut, GameUpdate, name_key

mcp = MCPServer(
    name="WhatToPlay",
    instructions=(
        "WhatToPlay is the user's video-game backlog: franchises containing games in play order. "
        "Always call get_instructions first and follow the user's instructions there. "
        "Before adding or changing anything, show the user the complete proposed list and wait for "
        "their explicit approval."
    ),
)


def session() -> Session:
    return Session(get_engine())


def app_errors(work):
    """Run app logic; turn its HTTP errors into plain messages for the assistant."""
    try:
        return work()
    except HTTPException as exc:
        raise ToolError(str(exc.detail)) from None


def find_franchise(s: Session, name: str) -> Franchise:
    for franchise in s.scalars(select(Franchise).options(*WITH_GAMES)):
        if name_key(franchise.name) == name_key(name):
            return franchise
    raise ToolError(f"No franchise named '{name}'. Use list_franchises to see the exact names.")


def find_game(franchise: Franchise, title: str) -> Game:
    for game in franchise.games:
        if name_key(game.title) == name_key(title):
            return game
    raise ToolError(f"No game titled '{title}' in '{franchise.name}'. Use get_franchise to see its games.")


@mcp.tool()
def get_instructions() -> str:
    """The user's instructions for adding games, plus the platform names and field rules. Call this first."""
    with session() as s:
        instructions = get_preference(s, "ai_instructions")
        platforms = s.scalars(select(Platform.name).order_by(Platform.sort_order)).all()
    return (
        f"{instructions}\n\n"
        "Data rules:\n"
        f"- Platform names must be exactly one of: {', '.join(platforms)}.\n"
        "- play_on must be one of the game's platforms (or empty).\n"
        "- status: unplayed, playing, finished or skip.\n"
        "- release_year + optional release_month (1-12); release_tba=true when the date isn't final.\n"
        "- length_hours: main-story time in whole hours (1-999), or empty when unknown.\n"
        "- Games are listed in play order; a franchise's games are added at its end."
    )


@mcp.tool()
def list_franchises() -> dict:
    """Every franchise with its number of games, how many are done, and the next game to play."""
    with session() as s:
        result = []
        for f in s.scalars(select(Franchise).order_by(Franchise.name).options(*WITH_GAMES)):
            open_games = [g for g in f.games if g.status.value not in ("finished", "skip")]
            result.append({
                "name": f.name,
                "games": len(f.games),
                "done": len(f.games) - len(open_games),
                "next_up": open_games[0].title if open_games else None,
            })
        return {"franchises": result}   # one object rather than a list: sent as a single block


@mcp.tool()
def get_franchise(name: str) -> dict:
    """One franchise with all its games in play order (titles, release, status, platforms, play on, notes)."""
    with session() as s:
        return FranchiseOut.from_model(find_franchise(s, name)).model_dump(mode="json")


@mcp.tool()
def list_games(
    status: Status | None = None,
    missing_length: bool = False,
    tba_only: bool = False,
    franchise: str | None = None,
) -> dict:
    """Games across all franchises (or one), optionally filtered: by status, only those
    without a length (to fill in), or only those whose release date is TBA (to re-check).
    """
    with session() as s:
        if franchise:
            franchises = [find_franchise(s, franchise)]
        else:
            franchises = s.scalars(select(Franchise).order_by(Franchise.name).options(*WITH_GAMES)).all()
        games = []
        for f in franchises:
            for g in f.games:
                if status and g.status != status:
                    continue
                if missing_length and g.length_hours is not None:
                    continue
                if tba_only and not g.release_tba:
                    continue
                out = GameOut.from_model(g)
                games.append({"franchise": f.name, "title": g.title, "status": g.status.value,
                              "released": out.released, "platforms": out.platforms,
                              "play_on": out.play_on, "length_hours": g.length_hours})
        return {"count": len(games), "games": games}


@mcp.tool()
def search_games(query: str) -> dict:
    """Find games whose title contains the text (ignoring case and accents), in any franchise.

    Use it to avoid duplicates, e.g. a game already listed under another franchise.
    """
    needle = name_key(query)
    with session() as s:
        return {"matches": [
            {"franchise": f.name, "title": g.title, "status": g.status.value,
             "released": GameOut.from_model(g).released}
            for f in s.scalars(select(Franchise).order_by(Franchise.name).options(*WITH_GAMES))
            for g in f.games
            if needle in name_key(g.title)
        ]}


@mcp.tool()
def add_franchise(name: str, games: list[GameCreate], notes: str = "") -> dict:
    """Create a new franchise with its games, in play order, all at once (nothing is created if one game is invalid).

    Only call this after the user approved the complete list.
    """
    data = FranchiseCreate(name=name, notes=notes, games=games)
    with session() as s:
        created = app_errors(lambda: create_franchise(data, s))
        return {"created": created.name, "games": [g.title for g in created.games]}


@mcp.tool()
def add_games(franchise: str, games: list[GameCreate]) -> dict:
    """Add games at the end of an existing franchise, in the given order, all at once.

    Only call this after the user approved the list.
    """
    with session() as s:
        target = find_franchise(s, franchise)
        known = platforms_by_name(s)
        position = next_sort_order(s, target.id)
        for offset, data in enumerate(games):
            game = Game(franchise_id=target.id, sort_order=position + offset)
            app_errors(lambda: apply_fields(s, game, data.model_dump(exclude_unset=True), known))
            s.add(game)
        s.commit()
        return {"franchise": target.name, "added": [g.title for g in games]}


@mcp.tool()
def update_game(franchise: str, title: str, changes: GameUpdate) -> dict:
    """Change one game: only the fields given in `changes` are changed.

    Only call this after the user approved the change.
    """
    with session() as s:
        game = find_game(find_franchise(s, franchise), title)
        updated = app_errors(lambda: update_game_endpoint(game.id, changes, s))
        return updated.model_dump(mode="json")


# The ASGI app mounted at /mcp. Requests are self-contained (stateless) with plain
# JSON answers. The host-name check is off: like the rest of the app this is meant
# for the home network, and the AI switch below is the lock.
mcp_asgi_app = mcp.streamable_http_app(
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def ai_enabled() -> bool:
    with session() as s:
        return bool(get_preference(s, "ai_enabled"))


class AISwitch:
    """Refuses every MCP request while the AI assistant switch is off in Settings."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not await anyio.to_thread.run_sync(ai_enabled):
            response = JSONResponse(
                {"error": "The AI assistant is turned off in WhatToPlay's Settings."}, status_code=403
            )
            return await response(scope, receive, send)
        await self.app(scope, receive, send)
