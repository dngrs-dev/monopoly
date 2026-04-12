from dataclasses import dataclass, field
from enum import Enum, auto

from engine.board import Board
from engine.player import Player
from engine.dice import Dice
from engine.events import Event
from engine.choices import (
    Choice,
    PayFineChoice,
    TryDoublesJailChoice,
    RollDiceChoice,
    UseGetOutOfJailFreeCardChoice,
    MakeTradeOfferChoice,
)
from engine.cards import GetOutOfJailFreeCard
from engine.tiles import JailTile
from engine.rules import Rules
from engine.auction import Auction
from engine.tradeoffer import TradeOffer


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
    rules: Rules = field(default_factory=Rules)
    auction: Auction | None = None
    trade_offer: TradeOffer | None = None

    def current_player(self) -> Player:
        return self.players[self.current_player_index]


def start_game(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    player = game.current_player()
    choices = [RollDiceChoice(player_id=player.id)]
    for p in game.players:
        if p.id != player.id and not p.bankrupt:
            choices.append(
                MakeTradeOfferChoice(player_id=player.id, receiving_player_id=p.id)
            )
    return game, [], choices


def end_turn(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    game.current_player_index = (game.current_player_index + 1) % len(game.players)
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    player = game.current_player()
    if player.in_jail:
        tile = game.board.get_tile(player.position)
        if not isinstance(tile, JailTile):
            raise ValueError("Player is in jail but not on a JailTile")
        else:
            choices = [
                PayFineChoice(player_id=player.id, fine=tile.fine),
                TryDoublesJailChoice(player_id=player.id),
            ]
            if any(isinstance(card, GetOutOfJailFreeCard) for card in player.cards):
                choices.append(UseGetOutOfJailFreeCardChoice(player_id=player.id))
    else:
        choices = [RollDiceChoice(player_id=player.id)]
        for p in game.players:
            if p.id != player.id and not p.bankrupt:
                choices.append(
                    MakeTradeOfferChoice(player_id=player.id, receiving_player_id=p.id)
                )
    return game, [], choices


def apply_command(game: Game, choice: Choice) -> tuple[Game, list[Event], list[Choice]]:
    from engine.choice_handlers import apply_choice

    return apply_choice(choice, game)
