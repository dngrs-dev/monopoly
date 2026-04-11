from dataclasses import asdict, is_dataclass
from typing import Any
from uuid import uuid4

from game import Game, apply_command, end_turn, TurnPhase
from choices import Choice


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

    def apply_choice_id(self, choice_id: str) -> dict[str, Any]:
        if choice_id not in self.choice_map:
            raise IllegalCommand("Unknown or expired choice_id")

        choice = self.choice_map[choice_id]

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