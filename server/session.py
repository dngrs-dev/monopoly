from dataclasses import asdict, is_dataclass, replace
from typing import Any
from uuid import uuid4

from engine.game import Game, apply_command, end_turn, TurnPhase
from engine.choices import Choice, SendTradeOfferChoice


class IllegalCommand(Exception):
    pass


def to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        d = asdict(obj)
        d["type"] = type(obj).__name__
        return d
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj

def _require_int(payload: dict[str, Any], key: str) -> int:
    if key not in payload:
        raise IllegalCommand(f"Missing required key '{key}' in payload")
    value = payload[key]
    if not isinstance(value, int):
        raise IllegalCommand(f"Expected integer for key '{key}' in payload")
    return value

def _require_int_list(payload: dict[str, Any], key: str) -> list[int]:
    if key not in payload:
        raise IllegalCommand(f"Missing required key '{key}' in payload")
    value = payload[key]
    if not isinstance(value, list) or not all(isinstance(x, int) for x in value):
        raise IllegalCommand(f"Expected list of integers for key '{key}' in payload")
    return value


class GameSession:
    def __init__(self, game: Game, room_id: str):
        self.room_id = room_id
        self.game = game

        self.choice_map: dict[str, Choice] = {}  # choice_id -> Choice
        self.issued_choices: list[dict[str, Any]] = []  # for client display

    def issue_choices(self, choices: list[Choice]) -> list[dict[str, Any]]:
        self.choice_map.clear()
        self.issued_choices = []
        for c in choices:
            cid = uuid4().hex
            self.choice_map[cid] = c
            self.issued_choices.append({"id": cid, "choice": to_jsonable(c)})
        return self.issued_choices

    def snapshot(self) -> dict[str, Any]:
        # Minimal snapshot
        return {
            "room_id": self.room_id,
            "turn_phase": self.game.turn_phase.name,
            "current_player_id": self.game.current_player().id,
            "players": [to_jsonable(p) for p in self.game.players],
            "board_size": self.game.board.size(),
            "tiles": [to_jsonable(t) for t in self.game.board.tiles],
            "auction": to_jsonable(self.game.auction) if self.game.auction else None,
        }

    def apply_choice_id(
        self, choice_id: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if choice_id not in self.choice_map:
            raise IllegalCommand("Unknown or expired choice_id")

        choice = self.choice_map[choice_id]
        
        if isinstance(choice, SendTradeOfferChoice):
            if payload is None:
                raise IllegalCommand("Missing payload for SendTradeOfferChoice")
            
            choice = replace(
                choice,
                offered_money=_require_int(payload, "offered_money"),
                requested_money=_require_int(payload, "requested_money"),
                offered_properties_positions=_require_int_list(payload, "offered_properties_positions"),
                requested_properties_positions=_require_int_list(payload, "requested_properties_positions"),
            )

        # Apply the engine command.
        self.game, events, choices = apply_command(self.game, choice)

        if self.game.turn_phase == TurnPhase.END_TURN:
            self.game, end_events, end_choices = end_turn(self.game)
            events = events + end_events
            choices = end_choices

        issued = self.issue_choices(choices)

        return {
            "events": [to_jsonable(e) for e in events],
            "snapshot": self.snapshot(),
            "choices": issued,
        }
