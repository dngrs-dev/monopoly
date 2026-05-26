import asyncio
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any

from fastapi import APIRouter, WebSocket, Depends
from fastapi.responses import FileResponse
from ..paths import WEB_ROOT
from ..dependecies import User
from ..jwt_utils import get_current_user

from engine.game import (
    Game,
    TurnPhase,
    start_game,
    end_turn,
    build_available_choices,
    apply_command,
)
from engine.choices import Choice
from engine.events import Event
from engine.tiles import (
    Tile,
    OwnableTile,
    StreetTile,
    RailroadTile,
    UtilityTile,
    StartTile,
    JailTile,
    PayTile,
)


router = APIRouter(prefix="/games", tags=["games"])


@router.get("/me")
async def my_game(current_user: User = Depends(get_current_user)):
    session = await game_sessions.get_user_session(current_user.id)
    if session is None:
        return {"active": False, "error": "User is not in a game"}
    
    player_id = session.user_to_player[current_user.id]
    player = session.game.get_player(player_id)
    
    if player.bankrupt:
        return {"active": False, "error": "User is bankrupt"}
    
    return {"active": True, "lobby_id": session.lobby_id}

@router.get("/{lobby_id}")
async def game_page(lobby_id: str):
    return FileResponse(WEB_ROOT / "games" / "index.html")


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    return value


def _serialize_dataclass(obj: Any) -> dict:
    if not is_dataclass(obj):
        raise ValueError("Object must be a dataclass instance")
    data = _normalize(asdict(obj))
    data["type"] = obj.__class__.__name__
    return data

def _serialize_tile(tile: Tile, position: int) -> dict:
    data = {
        "position": position,
        "type": tile.__class__.__name__,
        "name": tile.name,
    }

    if isinstance(tile, OwnableTile):
        data.update(
            {
                "price": tile.price,
                "owner": tile.owner,
                "mortgaged": tile.mortgaged,
            }
        )

    if isinstance(tile, StreetTile):
        data.update(
            {
                "group_id": tile.group_id,
                "improvement_level": tile.improvement_level,
                "rent_schedule": tile.rent_schedule,
            }
        )

    if isinstance(tile, RailroadTile):
        data.update(
            {
                "group_id": tile.group_id,
                "rent_schedule": tile.rent_schedule,
            }
        )

    if isinstance(tile, UtilityTile):
        data.update(
            {
                "group_id": tile.group_id,
                "rent_multiplier": tile.rent_multiplier,
            }
        )

    if isinstance(tile, StartTile):
        data.update({"pass_bonus": tile.pass_bonus, "land_bonus": tile.land_bonus})

    if isinstance(tile, JailTile):
        data.update({"skip_turns": tile.skip_turns, "fine": tile.fine})

    if isinstance(tile, PayTile):
        data.update({"amount": tile.amount})

    # ChanceTile / GoToJailTile / NoneTile: no extra fields needed

    return data

@dataclass
class GameSession:
    lobby_id: str
    game: Game
    user_to_player: dict[int, int]
    player_to_user: dict[int, int]
    available_choices: list[Choice] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def serialize_state(self) -> dict:
        current_player_id = self.game.current_player().id if self.game.players else None
        return {
            "turn_phase": self.game.turn_phase.name,
            "current_player_id": current_player_id,
            "players": [
                {
                    "id": player.id,
                    "balance": player.balance,
                    "position": player.position,
                    "skip_turns": player.skip_turns,
                    "bankrupt": player.bankrupt,
                    "in_jail": player.in_jail,
                    "cards": [_normalize(card) for card in player.cards],
                    "multiplier_cards": {
                        str(pos): mult for pos, mult in player.multiplier_cards.items()
                    },
                }
                for player in self.game.players
            ],
            "dice": {
                "last_roll": self.game.dice.last_roll,
                "last_roll_pair": list(self.game.dice.last_roll_pair),
            },
        }

    def serialize_events(self, events: list[Event]) -> list[dict]:
        return [_serialize_dataclass(event) for event in events]

    def serialize_choices_for_user(self, user_id: int) -> list[dict]:
        player_id = self.user_to_player.get(user_id)
        if player_id is None:
            return []
        return [
            _serialize_dataclass(choice)
            for choice in self.available_choices
            if getattr(choice, "player_id", None) == player_id
        ]
        
    def serialize_board(self) -> list[dict]:
        return [
            _serialize_tile(tile, index)
            for index, tile in enumerate(self.game.board.tiles)
        ]

    def _find_matching_choice(self, player_id: int, payload: dict) -> Choice | None:
        for choice in self.available_choices:
            if getattr(choice, "player_id", None) != player_id:
                continue
            if _serialize_dataclass(choice) == payload:
                return choice
        return None

    async def apply_choice_payload(self, user_id: int, payload: dict) -> list[Event]:
        async with self.lock:
            player_id = self.user_to_player.get(user_id)
            if player_id is None:
                raise ValueError("User is not part of this game")

            if not self.available_choices:
                self.available_choices = build_available_choices(self.game)

            choice = self._find_matching_choice(player_id, payload)
            if choice is None:
                raise ValueError("Invalid or unavailable choice")

            self.game, events, choices = apply_command(self.game, choice)

            if self.game.turn_phase == TurnPhase.END_TURN:
                self.game, end_events, end_choices = end_turn(self.game)
                events.extend(end_events)
                choices.extend(end_choices)

            if not choices and self.game.turn_phase == TurnPhase.AWAIT_CHOICE:
                choices = build_available_choices(self.game)

            self.available_choices = choices
            return events


class GameSessions:
    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, lobby_id: str, user_ids: list[int], game: Game) -> GameSession:
        async with self._lock:
            if lobby_id in self._sessions:
                raise ValueError("Game already started")

            user_to_player = {user_id: index for index, user_id in enumerate(user_ids)}
            player_to_user = {index: user_id for user_id, index in user_to_player.items()}

            game, _, choices = start_game(game)

            session = GameSession(
                lobby_id=lobby_id,
                game=game,
                user_to_player=user_to_player,
                player_to_user=player_to_user,
                available_choices=choices,
            )
            self._sessions[lobby_id] = session
            return session

    async def get(self, lobby_id: str) -> GameSession | None:
        async with self._lock:
            return self._sessions.get(lobby_id)

    async def has(self, lobby_id: str) -> bool:
        async with self._lock:
            return lobby_id in self._sessions

    async def remove(self, lobby_id: str) -> None:
        async with self._lock:
            self._sessions.pop(lobby_id, None)
            
    async def get_user_session(self, user_id: int) -> GameSession | None:
        async with self._lock:
            for session in self._sessions.values():
                if user_id in session.user_to_player:
                    return session
            return None

class GameHub:
    def __init__(self) -> None:
        self._connections: dict[str, dict[int, set[WebSocket]]] = {}
        self._lock = asyncio.Lock()

    async def add(self, lobby_id: str, user_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.setdefault(lobby_id, {}).setdefault(user_id, set()).add(ws)

    async def remove(self, lobby_id: str, user_id: int, ws: WebSocket) -> None:
        async with self._lock:
            user_map = self._connections.get(lobby_id, {})
            sockets = user_map.get(user_id, set())
            sockets.discard(ws)
            if not sockets:
                user_map.pop(user_id, None)
            if not user_map:
                self._connections.pop(lobby_id, None)

    async def snapshot(self, lobby_id: str) -> dict[int, list[WebSocket]]:
        async with self._lock:
            return {
                user_id: list(sockets)
                for user_id, sockets in self._connections.get(lobby_id, {}).items()
            }

    async def broadcast(self, lobby_id: str, message: dict) -> None:
        user_map = await self.snapshot(lobby_id)
        for sockets in user_map.values():
            for ws in list(sockets):
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


game_sessions = GameSessions()
game_hub = GameHub()