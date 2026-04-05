from dataclasses import dataclass
from enum import Enum, auto

from board import Board
from player import Player
from dice import Dice
from events import Event
from choices import (
    Choice,
    PayFineChoice,
    TryDoublesJailChoice,
    RollDiceChoice,
)


class TurnPhase(Enum):
    RESOLVE_TILE = auto()
    AWAIT_CHOICE = auto()
    END_TURN = auto()


@dataclass
class Game:
    board: Board
    players: list[Player]
    dice: Dice
    current_player_index: int = 0
    turn_phase: TurnPhase = TurnPhase.AWAIT_CHOICE

    def current_player(self) -> Player:
        return self.players[self.current_player_index]


def start_game(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    choices = [RollDiceChoice(player_id=game.current_player().id)]
    return game, [], choices


def end_turn(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    game.current_player_index = (game.current_player_index + 1) % len(game.players)
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    if game.current_player().in_jail:
        choices = [
            PayFineChoice(player_id=game.current_player().id, fine=50),
            TryDoublesJailChoice(player_id=game.current_player().id),
        ]
    else:
        choices = [RollDiceChoice(player_id=game.current_player().id)]
    return game, [], choices


def apply_command(game: Game, choice: Choice) -> tuple[Game, list[Event], list[Choice]]:
    from choice_handlers import apply_choice

    return apply_choice(choice, game)
