import asyncio
from typing import Any
from pathlib import Path
from uuid import uuid4
import time
import secrets

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
    UploadFile,
    File,
)
from fastapi.responses import FileResponse, RedirectResponse
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
from server.protocol import (
    is_join,
    is_choose,
    is_lobby_create,
    is_lobby_join,
    is_lobby_join_invite,
    is_lobby_leave,
    is_lobby_start,
    is_lobby_list,
)
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


async def _get_user_optional(request: Request) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
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


def _avatar_path(user_id: str) -> Path:
    return AVATAR_DIR / f"{user_id}.png"


def _avatar_response_for(user: User) -> Response | FileResponse:
    path = _avatar_path(user.id)
    headers = {"Cache-Control": "no-store"}
    if path.exists():
        return FileResponse(path, media_type="image/png", headers=headers)
    return FileResponse(DEFAULT_AVATAR_PATH, media_type="image/svg+xml", headers=headers)


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
AVATAR_DIR = _REPO_ROOT / ".data" / "avatars"
DEFAULT_AVATAR_PATH = _WEB_DIR / "profile" / "avatar-default.svg"
AVATAR_MAX_BYTES = 1024 * 1024

DB_PATH = os.getenv("MONOPOLY_DB_PATH", str(_REPO_ROOT / ".data" / "monopoly.db"))
auth_db = AuthDb(DB_PATH)


@app.on_event("startup")
def _startup() -> None:
    auth_db.init()
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.create_task(_lobby_cleanup_loop())


app.mount("/static", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")

DEFAULT_PLAYER_COUNT = 2
DEFAULT_START_BALANCE = 500

LOBBY_LIMIT_MIN = 1
LOBBY_LIMIT_MAX = 8
LOBBY_DEFAULT_LIMIT = 4
LOBBY_TTL_SECONDS = 60 * 10
LOBBY_CLEANUP_INTERVAL_SECONDS = 30

INVITE_CODE_LENGTH = 6
INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

rooms_lock = asyncio.Lock()
rooms: dict[str, dict[str, Any]] = {}
# rooms[room_id] = {
#   "session": GameSession,
#   "clients": set[WebSocket],
#   "user_to_player": dict[str, int],
#   "player_to_user": dict[int, str],
#   "allowed_user_ids": set[str] | None,
#   "created_from_lobby_id": str | None,
# }

lobbies_lock = asyncio.Lock()
lobbies: dict[str, dict[str, Any]] = {}
# lobbies[lobby_id] = {
#   "owner_user_id": str,
#   "is_public": bool,
#   "invite_code": str | None,
#   "user_limit": int,
#   "members": dict[str, dict[str, str]],
#   "member_order": list[str],
#   "member_connections": dict[str, int],
#   "clients": set[WebSocket],
#   "client_users": dict[WebSocket, str],
#   "started": bool,
#   "room_id": str | None,
#   "last_activity": float,
# }

lobby_watchers: set[WebSocket] = set()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


@app.get("/login")
async def login_page() -> FileResponse:
    return FileResponse(_WEB_DIR / "login" / "index.html")


@app.get("/game")
async def game_page() -> FileResponse:
    return FileResponse(_WEB_DIR / "game" / "index.html")


@app.get("/profile")
async def profile_page(request: Request):
    try:
        user = await _require_user_http(request)
    except HTTPException:
        return RedirectResponse("/", status_code=302)

    return RedirectResponse(f"/profile/{user.handle}", status_code=302)


@app.get("/profile/{handle}")
async def profile_page_handle(handle: str):
    return FileResponse(_WEB_DIR / "profile" / "index.html")


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
        "user": {
            "user_id": user.id,
            "username": user.username,
            "handle": user.handle,
            "email": user.email,
        },
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
        "user": {
            "user_id": user.id,
            "username": user.username,
            "handle": user.handle,
            "email": user.email,
        },
    }


@app.get("/api/auth/me")
async def auth_me(request: Request):
    user = await _require_user_http(request)
    return {
        "user_id": user.id,
        "username": user.username,
        "handle": user.handle,
        "email": user.email,
    }


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
            "handle": updated.handle,
            "email": updated.email,
        },
    }


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/profile/me")
async def profile_me(request: Request):
    user = await _require_user_http(request)
    stats = await run_in_threadpool(auth_db.get_user_stats, user.id)
    history = await run_in_threadpool(auth_db.get_username_history, user.id)
    return {
        "user_id": user.id,
        "username": user.username,
        "handle": user.handle,
        "stats": stats,
        "history": history,
        "is_self": True,
        "profile_link": f"/profile/{user.handle}",
    }


@app.get("/api/profile/handle/{handle}")
async def profile_by_handle(handle: str, request: Request):
    viewer = await _get_user_optional(request)
    target = await run_in_threadpool(auth_db.get_user_by_handle, handle)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    stats = await run_in_threadpool(auth_db.get_user_stats, target.id)
    history: list[dict[str, str]] = []
    is_self = viewer is not None and viewer.id == target.id
    if is_self:
        history = await run_in_threadpool(auth_db.get_username_history, target.id)

    return {
        "user_id": target.id,
        "username": target.username,
        "handle": target.handle,
        "stats": stats,
        "history": history,
        "is_self": is_self,
        "profile_link": f"/profile/{target.handle}",
    }


@app.get("/api/profile/avatar")
async def get_avatar(request: Request):
    user = await _require_user_http(request)
    return _avatar_response_for(user)


@app.get("/api/profile/avatar/{handle}")
async def get_avatar_by_handle(handle: str):
    target = await run_in_threadpool(auth_db.get_user_by_handle, handle)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _avatar_response_for(target)


@app.post("/api/profile/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    user = await _require_user_http(request)
    if file.content_type != "image/png":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be a PNG image",
        )

    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload"
        )
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar must be 1MB or smaller",
        )

    path = _avatar_path(user.id)
    path.write_bytes(data)
    return {"ok": True}


@app.delete("/api/profile/avatar")
async def delete_avatar(request: Request):
    user = await _require_user_http(request)
    path = _avatar_path(user.id)
    if path.exists():
        path.unlink()
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


def _build_player_list(member_count: int) -> list[Player]:
    return [
        Player(id=index + 1, balance=DEFAULT_START_BALANCE)
        for index in range(member_count)
    ]


async def get_or_create_room(room_id: str, *, player_count: int) -> dict[str, Any]:
    async with rooms_lock:
        if room_id in rooms:
            return rooms[room_id]

        board = build_demo_board()
        game = Game(
            board=board,
            players=_build_player_list(player_count),
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
            "allowed_user_ids": None,  # optional set[str]
            "created_from_lobby_id": None,
        }
        return rooms[room_id]


def _lobby_snapshot(
    lobby_id: str,
    lobby: dict[str, Any],
    *,
    include_invite_code: bool = True,
    include_idle_expires: bool = True,
) -> dict[str, Any]:
    members = [lobby["members"][uid] for uid in lobby["member_order"]]
    owner_member = lobby["members"].get(lobby["owner_user_id"])
    owner_username = owner_member["username"] if owner_member else None
    idle_expires_at = lobby.get("last_activity", _now_ts()) + LOBBY_TTL_SECONDS
    payload = {
        "lobby_id": lobby_id,
        "owner_user_id": lobby["owner_user_id"],
        "owner_username": owner_username,
        "is_public": lobby["is_public"],
        "user_limit": lobby["user_limit"],
        "started": lobby["started"],
        "room_id": lobby["room_id"],
        "members": members,
    }
    if include_invite_code:
        payload["invite_code"] = lobby["invite_code"]
    if include_idle_expires:
        payload["idle_expires_at"] = idle_expires_at
    return payload


async def _broadcast_lobby(lobby: dict[str, Any], payload: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    for ws in list(lobby["clients"]):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        lobby["clients"].discard(ws)


def _public_lobby_list() -> list[dict[str, Any]]:
    return [
        _lobby_snapshot(
            lobby_id, lobby, include_invite_code=False, include_idle_expires=False
        )
        for lobby_id, lobby in lobbies.items()
        if lobby["is_public"] and not lobby["started"]
    ]


async def _broadcast_lobby_list() -> None:
    async with lobbies_lock:
        if not lobby_watchers:
            return
        payload = {"type": "lobby_list", "lobbies": _public_lobby_list()}
        targets = list(lobby_watchers)

    dead: list[WebSocket] = []
    for ws in targets:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)

    if dead:
        async with lobbies_lock:
            for ws in dead:
                lobby_watchers.discard(ws)


def _now_ts() -> float:
    return time.time()


def _generate_invite_code() -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


def _allocate_invite_code() -> str:
    for _ in range(1000):
        code = _generate_invite_code()
        if all(lobby.get("invite_code") != code for lobby in lobbies.values()):
            return code
    raise RuntimeError("Failed to allocate unique invite code")


async def _lobby_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(LOBBY_CLEANUP_INTERVAL_SECONDS)
        now = _now_ts()

        expired: list[tuple[dict[str, Any], list[WebSocket], dict[WebSocket, str]]] = []

        async with lobbies_lock:
            for lobby_id, lobby in list(lobbies.items()):
                if lobby["started"]:
                    continue
                last_activity = float(lobby.get("last_activity", now))
                if now - last_activity < LOBBY_TTL_SECONDS:
                    continue

                clients = list(lobby["clients"])
                client_users = dict(lobby.get("client_users", {}))
                expired.append((lobby, clients, client_users))
                del lobbies[lobby_id]

        if not expired:
            continue

        for lobby, clients, client_users in expired:
            owner_id = lobby["owner_user_id"]
            for ws in clients:
                user_id = client_users.get(ws)
                payload = {
                    "type": "lobby_closed",
                    "message": "Lobby closed due to inactivity (10 minutes).",
                }
                if user_id == owner_id:
                    payload["owner_message"] = (
                        "Your lobby closed due to inactivity (10 minutes). "
                        "Create a new lobby to continue."
                    )
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass

        await _broadcast_lobby_list()


def _clamp_user_limit(value: int | None) -> int:
    if value is None:
        return LOBBY_DEFAULT_LIMIT
    if not isinstance(value, int):
        return LOBBY_DEFAULT_LIMIT
    if value < LOBBY_LIMIT_MIN:
        return LOBBY_LIMIT_MIN
    if value > LOBBY_LIMIT_MAX:
        return LOBBY_LIMIT_MAX
    return value


def _make_room_id() -> str:
    return f"room_{uuid4().hex}"


async def _create_room_for_lobby(
    *, lobby_id: str, room_id: str, member_order: list[str]
) -> None:
    room = await get_or_create_room(room_id, player_count=len(member_order))
    async with rooms_lock:
        room["allowed_user_ids"] = set(member_order)
        room["created_from_lobby_id"] = lobby_id

        user_to_player: dict[str, int] = room["user_to_player"]
        player_to_user: dict[int, str] = room["player_to_user"]
        user_to_player.clear()
        player_to_user.clear()

        for index, user_id in enumerate(member_order):
            player_id = index + 1
            user_to_player[user_id] = player_id
            player_to_user[player_id] = user_id


async def _leave_lobby_connection(
    *, ws: WebSocket, lobby_id: str, user_id: str
) -> None:
    update_payload: dict[str, Any] | None = None
    update_clients: list[WebSocket] | None = None
    closed_clients: list[WebSocket] | None = None

    async with lobbies_lock:
        lobby = lobbies.get(lobby_id)
        if not lobby:
            return

        lobby["clients"].discard(ws)
        lobby["client_users"].pop(ws, None)

        connections: dict[str, int] = lobby["member_connections"]
        member_removed = False
        if user_id in connections:
            connections[user_id] = max(0, connections[user_id] - 1)
            if connections[user_id] == 0:
                del connections[user_id]
                lobby["members"].pop(user_id, None)
                if user_id in lobby["member_order"]:
                    lobby["member_order"] = [
                        uid for uid in lobby["member_order"] if uid != user_id
                    ]
                member_removed = True

        if member_removed:
            lobby["last_activity"] = _now_ts()

        owner_left = (
            user_id == lobby["owner_user_id"] and user_id not in connections
        )

        if owner_left and not lobby["started"]:
            closed_clients = list(lobby["clients"])
            del lobbies[lobby_id]
        else:
            update_payload = {
                "type": "lobby_update",
                "lobby": _lobby_snapshot(lobby_id, lobby),
            }
            update_clients = list(lobby["clients"])

    if closed_clients:
        for client in closed_clients:
            try:
                await client.send_json(
                    {
                        "type": "lobby_closed",
                        "message": "Lobby closed because the owner left.",
                    }
                )
            except Exception:
                pass

    if update_payload and update_clients:
        for client in update_clients:
            try:
                await client.send_json(update_payload)
            except Exception:
                pass

    await _broadcast_lobby_list()


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
    joined_lobby: dict[str, Any] | None = None
    lobby_id: str | None = None

    try:
        while True:
            msg = await ws.receive_json()

            if joined_lobby is not None and lobby_id is not None:
                async with lobbies_lock:
                    if lobby_id not in lobbies:
                        joined_lobby = None
                        lobby_id = None

            if is_lobby_list(msg):
                async with lobbies_lock:
                    lobby_watchers.add(ws)
                    payload = {
                        "type": "lobby_list",
                        "lobbies": _public_lobby_list(),
                    }
                await ws.send_json(payload)
                continue

            if is_lobby_create(msg):
                if joined_lobby is not None:
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": "Already joined to a lobby",
                        }
                    )
                    continue

                if joined_room is not None:
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": "Cannot create a lobby while in a game",
                        }
                    )
                    continue

                user_limit = _clamp_user_limit(msg.get("user_limit"))
                is_public = msg.get("is_public")
                if not isinstance(is_public, bool):
                    is_public = True
                new_lobby_id = uuid4().hex
                lobby_snapshot: dict[str, Any]

                async with lobbies_lock:
                    invite_code = None
                    if not is_public:
                        invite_code = _allocate_invite_code()

                    lobby = {
                        "owner_user_id": user.id,
                        "is_public": is_public,
                        "invite_code": invite_code,
                        "user_limit": user_limit,
                        "members": {
                            user.id: {
                                "user_id": user.id,
                                "username": user.username,
                            }
                        },
                        "member_order": [user.id],
                        "member_connections": {user.id: 1},
                        "clients": {ws},
                        "client_users": {ws: user.id},
                        "started": False,
                        "room_id": None,
                        "last_activity": _now_ts(),
                    }
                    lobbies[new_lobby_id] = lobby
                    lobby_snapshot = _lobby_snapshot(new_lobby_id, lobby)

                joined_lobby = lobby
                lobby_id = new_lobby_id

                await ws.send_json(
                    {
                        "type": "lobby_joined",
                        "lobby": lobby_snapshot,
                        "you": {
                            "user_id": user.id,
                            "username": user.username,
                            "role": "owner",
                        },
                    }
                )
                await _broadcast_lobby_list()
                continue

            if is_lobby_join_invite(msg) or is_lobby_join(msg):
                target_lobby_id: str | None = None
                join_via_invite = False

                if is_lobby_join_invite(msg):
                    join_via_invite = True
                    invite_code = str(msg["invite_code"]).strip().upper()
                    if not invite_code:
                        await ws.send_json(
                            {"type": "error", "message": "Invite code is required"}
                        )
                        continue

                    async with lobbies_lock:
                        for candidate_id, candidate in lobbies.items():
                            if candidate.get("invite_code") == invite_code:
                                target_lobby_id = candidate_id
                                break

                    if not target_lobby_id:
                        await ws.send_json(
                            {"type": "error", "message": "Invite code not found"}
                        )
                        continue
                else:
                    target_lobby_id = str(msg["lobby_id"]).strip()
                    if not target_lobby_id:
                        await ws.send_json(
                            {"type": "error", "message": "Lobby id is required"}
                        )
                        continue

                if joined_lobby is not None and lobby_id != target_lobby_id:
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": "Already joined to a different lobby",
                        }
                    )
                    continue

                lobby_snapshot = None
                notify_payload = None
                notify_clients: list[WebSocket] | None = None
                role = "member"
                error_message: str | None = None
                started_room_id: str | None = None
                member_added = False

                async with lobbies_lock:
                    lobby = lobbies.get(target_lobby_id)
                    if not lobby:
                        error_message = "Lobby not found"
                    elif lobby["started"]:
                        if user.id not in lobby["members"]:
                            error_message = "Lobby already started"
                        else:
                            started_room_id = lobby.get("room_id")
                            if not started_room_id:
                                error_message = "Lobby start in progress"
                    else:
                        if (
                            not lobby["is_public"]
                            and not join_via_invite
                            and user.id not in lobby["members"]
                        ):
                            error_message = "Private lobby. Use an invite code."
                        elif user.id not in lobby["members"]:
                            if len(lobby["members"]) >= lobby["user_limit"]:
                                error_message = "Lobby is full"
                            else:
                                lobby["members"][user.id] = {
                                    "user_id": user.id,
                                    "username": user.username,
                                }
                                lobby["member_order"].append(user.id)
                                member_added = True

                        if error_message is None:
                            lobby["member_connections"][user.id] = (
                                lobby["member_connections"].get(user.id, 0) + 1
                            )
                            lobby["clients"].add(ws)
                            lobby["client_users"][ws] = user.id

                            if member_added:
                                lobby["last_activity"] = _now_ts()

                            lobby_snapshot = _lobby_snapshot(target_lobby_id, lobby)
                            role = (
                                "owner"
                                if user.id == lobby["owner_user_id"]
                                else "member"
                            )
                            notify_payload = {
                                "type": "lobby_update",
                                "lobby": lobby_snapshot,
                            }
                            notify_clients = list(lobby["clients"])

                            joined_lobby = lobby
                            lobby_id = target_lobby_id

                if error_message:
                    await ws.send_json({"type": "error", "message": error_message})
                    continue

                if started_room_id:
                    await ws.send_json(
                        {"type": "lobby_started", "room_id": started_room_id}
                    )
                    continue

                await ws.send_json(
                    {
                        "type": "lobby_joined",
                        "lobby": lobby_snapshot,
                        "you": {
                            "user_id": user.id,
                            "username": user.username,
                            "role": role,
                        },
                    }
                )

                if notify_payload and notify_clients:
                    for client in notify_clients:
                        try:
                            await client.send_json(notify_payload)
                        except Exception:
                            pass
                await _broadcast_lobby_list()
                continue

            if is_lobby_leave(msg):
                target_lobby_id = str(msg["lobby_id"]).strip()
                if joined_lobby is None or lobby_id != target_lobby_id:
                    await ws.send_json(
                        {"type": "error", "message": "Not in that lobby"}
                    )
                    continue

                await _leave_lobby_connection(
                    ws=ws, lobby_id=target_lobby_id, user_id=user.id
                )
                joined_lobby = None
                lobby_id = None
                continue

            if is_lobby_start(msg):
                target_lobby_id = str(msg["lobby_id"]).strip()
                if joined_lobby is None or lobby_id != target_lobby_id:
                    await ws.send_json(
                        {"type": "error", "message": "Not in that lobby"}
                    )
                    continue

                member_order: list[str] | None = None
                target_room_id: str | None = None
                notify_clients: list[WebSocket] | None = None
                error_message: str | None = None

                async with lobbies_lock:
                    lobby = lobbies.get(target_lobby_id)
                    if not lobby:
                        error_message = "Lobby not found"
                    elif user.id != lobby["owner_user_id"]:
                        error_message = "Only the owner can start the lobby"
                    elif lobby["started"]:
                        target_room_id = lobby.get("room_id")
                        notify_clients = list(lobby["clients"])
                        if not target_room_id:
                            error_message = "Lobby start in progress"
                    else:
                        lobby["started"] = True
                        lobby["last_activity"] = _now_ts()
                        member_order = list(lobby["member_order"])
                        target_room_id = _make_room_id()
                        lobby["room_id"] = target_room_id
                        notify_clients = list(lobby["clients"])

                if error_message:
                    await ws.send_json({"type": "error", "message": error_message})
                    continue

                if not target_room_id:
                    await ws.send_json(
                        {"type": "error", "message": "Lobby start failed"}
                    )
                    continue

                if member_order is not None:
                    await _create_room_for_lobby(
                        lobby_id=target_lobby_id,
                        room_id=target_room_id,
                        member_order=member_order,
                    )

                if notify_clients:
                    for client in notify_clients:
                        try:
                            await client.send_json(
                                {
                                    "type": "lobby_started",
                                    "room_id": target_room_id,
                                }
                            )
                        except Exception:
                            pass
                await _broadcast_lobby_list()
                continue

            if is_join(msg):
                room_id = msg["room_id"]
                joined_room = await get_or_create_room(
                    room_id, player_count=DEFAULT_PLAYER_COUNT
                )

                allowed_user_ids: set[str] | None = joined_room.get(
                    "allowed_user_ids"
                )
                if allowed_user_ids is not None and user.id not in allowed_user_ids:
                    joined_room = None
                    room_id = None
                    player_id = None
                    await ws.send_json(
                        {
                            "type": "error",
                            "message": "Room is limited to lobby members",
                        }
                    )
                    continue

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
        if joined_lobby is not None and lobby_id is not None:
            await _leave_lobby_connection(
                ws=ws, lobby_id=lobby_id, user_id=user.id
            )
        async with lobbies_lock:
            lobby_watchers.discard(ws)
