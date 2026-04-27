import asyncio
from typing import Any
from pathlib import Path

import os
from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from starlette.concurrency import run_in_threadpool

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
from engine.tiles import StartTile, OwnableTile, ChanceTile, JailTile, GoToJailTile
from engine.player import Player
from engine.game import Game, start_game
from engine.rules import Rules

from server.session import GameSession, IllegalCommand
from server.protocol import is_join, is_choose
from server.auth_db import AuthDb, User, normalize_email


load_dotenv()
app = FastAPI()

COOKIE_NAME = "monopoly_session"
JWT_SECRET = os.getenv("MONOPOLY_JWT_SECRET", "something-secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
COOKIE_SECURE = os.getenv("MONOPOLY_COOKIE_SECURE", "0") == "1"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_token(*, user_id: str) -> str:
    now = _utcnow()
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _parse_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        return None

    return user_id


async def _require_user_http(request: Request) -> User:
    token = request.cookies.get(COOKIE_NAME)
    user_id = _parse_token(token) if token else None
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    user = await run_in_threadpool(auth_db.get_user_by_id, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    return user


async def _require_user_ws(ws: WebSocket) -> User | None:
    token = ws.cookies.get(COOKIE_NAME)
    user_id = _parse_token(token) if token else None
    if not user_id:
        return None
    return await run_in_threadpool(auth_db.get_user_by_id, user_id)


def _validate_email(value: str) -> str:
    email = normalize_email(value)
    if not (3 <= len(email) <= 320):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email"
        )
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email"
        )
    return email


def _validate_password(value: str) -> str:
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password"
        )
    if not (8 <= len(value) <= 256):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be between 8 and 256 characters",
        )
    return value


def _validate_username(value: str) -> str:
    username = value.strip()
    if not (1 <= len(username) <= 32):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 1 and 32 characters",
        )
    return username


class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class UpdateUsernameIn(BaseModel):
    username: str


_REPO_ROOT = Path(__file__).resolve().parents[1]
_WEB_DIR = _REPO_ROOT / "clients" / "web"

DB_PATH = os.getenv("MONOPOLY_DB_PATH", str(_REPO_ROOT / ".data" / "monopoly.db"))
auth_db = AuthDb(DB_PATH)


@app.on_event("startup")
def _startup() -> None:
    auth_db.init()


app.mount("/static", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")

rooms_lock = asyncio.Lock()
rooms: dict[str, dict[str, Any]] = {}
# rooms[room_id] = { "session": GameSession, "clients": set[WebSocket] }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


@app.get("/login")
async def login_page() -> FileResponse:
    return FileResponse(_WEB_DIR / "login" / "index.html")


@app.get("/game")
async def game_page() -> FileResponse:
    return FileResponse(_WEB_DIR / "game" / "index.html")


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, response: Response):
    email = _validate_email(data.email)
    password = _validate_password(data.password)

    try:
        user = await run_in_threadpool(auth_db.create_user, email=email, password=password)
    except ValueError as e:
        message = str(e)
        conflict = "already exists" in message.lower()
        code = status.HTTP_409_CONFLICT if conflict else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=message) from e

    token = _make_token(user_id=user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=ACCESS_TOKEN_TTL_SECONDS,
        path="/",
    )

    return {
        "ok": True,
        "user": {"user_id": user.id, "username": user.username, "email": user.email},
    }


@app.post("/api/auth/login")
async def login(data: LoginIn, response: Response):
    email = _validate_email(data.email)
    password = _validate_password(data.password)

    user = await run_in_threadpool(auth_db.authenticate, email=email, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    token = _make_token(user_id=user.id)

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=ACCESS_TOKEN_TTL_SECONDS,
        path="/",
    )
    return {
        "ok": True,
        "user": {"user_id": user.id, "username": user.username, "email": user.email},
    }


@app.get("/api/auth/me")
async def auth_me(request: Request):
    user = await _require_user_http(request)
    return {"user_id": user.id, "username": user.username, "email": user.email}


@app.post("/api/auth/username")
async def update_username(data: UpdateUsernameIn, request: Request):
    user = await _require_user_http(request)
    username = _validate_username(data.username)
    try:
        updated = await run_in_threadpool(
            auth_db.update_username, user_id=user.id, username=username
        )
    except ValueError as e:
        message = str(e)
        conflict = "already exists" in message.lower()
        code = status.HTTP_409_CONFLICT if conflict else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=message) from e

    return {
        "ok": True,
        "user": {
            "user_id": updated.id,
            "username": updated.username,
            "email": updated.email,
        },
    }


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


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
            OwnableTile(name="Mediterranean Avenue", price=60, rent=2),
            ChanceTile(name="Chance", deck=deck),
            OwnableTile(name="Baltic Avenue", price=60, rent=4),
            JailTile(name="Jail"),
            OwnableTile(name="Oriental Avenue", price=100, rent=6),
            GoToJailTile(name="Go To Jail"),
            OwnableTile(name="Vermont Avenue", price=100, rent=6),
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

        rooms[room_id] = {
            "session": session,
            "clients": set(),
            "user_to_player": {},  # user_id -> player_id
            "player_to_user": {},  # player_id -> user_id
        }
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
    user = await _require_user_ws(ws)
    if not user:
        await ws.close(code=1008)
        return

    await ws.accept()

    joined_room: dict[str, Any] | None = None
    room_id: str | None = None
    player_id: int | None = None

    try:
        while True:
            msg = await ws.receive_json()

            if is_join(msg):
                room_id = msg["room_id"]
                joined_room = await get_or_create_room(room_id)

                async with rooms_lock:
                    joined_room["clients"].add(ws)
                    session: GameSession = joined_room["session"]

                    user_to_player: dict[str, int] = joined_room["user_to_player"]
                    player_to_user: dict[int, str] = joined_room["player_to_user"]

                    if user.id in user_to_player:
                        player_id = user_to_player[user.id]
                    else:
                        taken = set(player_to_user.keys())
                        free = [p.id for p in session.game.players if p.id not in taken]
                        if free:
                            player_id = free[0]
                            user_to_player[user.id] = player_id
                            player_to_user[player_id] = user.id
                        else:
                            player_id = None  # spectator

                await ws.send_json(
                    {
                        "type": "joined",
                        "room_id": room_id,
                        "you": {
                            "user_id": user.id,
                            "username": user.username,
                            "player_id": player_id,
                            "role": "player" if player_id is not None else "spectator",
                        },
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

                if player_id is None:
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": "Room is full (spectator). You cannot make moves.",
                        }
                    )
                    continue

                session: GameSession = joined_room["session"]
                choice_id = msg["choice_id"]

                choice = session.choice_map.get(choice_id)
                if choice is None:
                    await ws.send_json(
                        {"type": "error", "message": "Unknown or expired choice_id"}
                    )
                    continue

                owner = getattr(choice, "player_id", None)
                if owner != player_id:
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": "That choice is not for your player",
                        }
                    )
                    continue

                try:
                    result = session.apply_choice_id(choice_id, msg.get("payload"))
                except IllegalCommand as e:
                    await ws.send_json({"type": "error", "message": str(e)})
                    continue
                except Exception as e:
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
            async with rooms_lock:
                joined_room["clients"].discard(ws)
