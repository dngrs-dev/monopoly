import asyncio
from typing import Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from engine.board import Board
from engine.dice import Dice
from engine.deck import Deck
from engine.cards import (
    MoveStepsCard,
    MoveToPositionCard,
    MoneyCard,
    GoToJailCard,
    GetOutOfJailFreeCard,
)
from engine.tiles import StartTile, PropertyTile, ChanceTile, JailTile, GoToJailTile
from engine.player import Player
from engine.game import Game, start_game
from engine.rules import Rules

from server.session import GameSession, IllegalCommand
from server.protocol import is_join, is_choose


app = FastAPI()

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WEB_DIR = _REPO_ROOT / "clients" / "web"

app.mount("/static", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")

rooms_lock = asyncio.Lock()
rooms: dict[str, dict[str, Any]] = {}
# rooms[room_id] = { "session": GameSession, "clients": set[WebSocket] }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


def build_demo_deck() -> Deck:
    return Deck(
        cards=[
            MoveStepsCard(steps=3),
            MoveToPositionCard(position=5),
            MoneyCard(amount=100),
            GoToJailCard(),
            GetOutOfJailFreeCard(),
        ]
    )


def build_demo_board() -> Board:
    deck = build_demo_deck()
    return Board(
        tiles=[
            StartTile(name="Start"),
            PropertyTile(name="Mediterranean Avenue", price=60, rent=2),
            ChanceTile(name="Chance", deck=deck),
            PropertyTile(name="Baltic Avenue", price=60, rent=4),
            JailTile(name="Jail"),
            PropertyTile(name="Oriental Avenue", price=100, rent=6),
            GoToJailTile(name="Go To Jail"),
            PropertyTile(name="Vermont Avenue", price=100, rent=6),
        ]
    )


async def get_or_create_room(room_id: str) -> dict[str, Any]:
    async with rooms_lock:
        if room_id in rooms:
            return rooms[room_id]

        board = build_demo_board()
        game = Game(
            board=board,
            players=[Player(id=1, balance=500), Player(id=2, balance=500)],
            dice=Dice(),
            rules=Rules(auction_enabled=True),
        )

        game, events, choices = start_game(game)
        session = GameSession(game=game, room_id=room_id)
        session.issue_choices(choices)

        rooms[room_id] = {"session": session, "clients": set()}
        return rooms[room_id]


async def broadcast(room: dict[str, Any], payload: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    for ws in list(room["clients"]):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        room["clients"].discard(ws)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    joined_room: dict[str, Any] | None = None
    room_id: str | None = None

    try:
        while True:
            msg = await ws.receive_json()

            if is_join(msg):
                room_id = msg["room_id"]
                joined_room = await get_or_create_room(room_id)
                joined_room["clients"].add(ws)

                session: GameSession = joined_room["session"]

                await ws.send_json(
                    {
                        "type": "joined",
                        "room_id": room_id,
                        "snapshot": session.snapshot(),
                        "choices": session.issued_choices,
                    }
                )
                continue

            if is_choose(msg):
                if joined_room is None or room_id != msg["room_id"]:
                    await ws.send_json(
                        {"type": "error", "message": "Not joined to that room"}
                    )
                    continue

                session: GameSession = joined_room["session"]
                try:
                    result = session.apply_choice_id(
                        msg["choice_id"], msg.get("payload")
                    )
                except IllegalCommand as e:
                    await ws.send_json({"type": "error", "message": str(e)})
                    continue
                except Exception as e:
                    # Avoid leaking internals in production; OK for dev.
                    await ws.send_json(
                        {"type": "error", "message": f"Server error: {e}"}
                    )
                    continue

                await broadcast(
                    joined_room,
                    {
                        "type": "update",
                        "room_id": room_id,
                        **result,
                    },
                )
                continue

            await ws.send_json({"type": "error", "message": "Unknown message type"})

    except WebSocketDisconnect:
        pass
    finally:
        if joined_room is not None:
            joined_room["clients"].discard(ws)
