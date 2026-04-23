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
    BuyImprovementChoice,
    SellImprovementChoice,
    MortgagePropertyChoice,
    UnmortgagePropertyChoice,
)
from engine.cards import GetOutOfJailFreeCard
from engine.tiles import JailTile, StreetTile, OwnableTile
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
    # Add buy improvement choices for properties that can be improved
    for tile in game.board.tiles:
        if isinstance(tile, StreetTile):
            if tile.owner == player.id:
                group_tiles = game.board.get_group_tiles(tile.group_id)
                if all(t.owner == player.id for t in group_tiles):
                    if tile.improvement_level < len(tile.rent_schedule) - 1:
                        choices.append(
                            BuyImprovementChoice(
                                player_id=player.id,
                                tile_position=game.board.tiles.index(tile),
                            )
                        )
                    if tile.improvement_level > 0:
                        choices.append(
                            SellImprovementChoice(
                                player_id=player.id,
                                tile_position=game.board.tiles.index(tile),
                            )
                        )
        if isinstance(tile, OwnableTile):
            if tile.owner == player.id and not tile.mortgaged:
                choices.append(
                    MortgagePropertyChoice(
                        player_id=player.id,
                        property_position=game.board.tiles.index(tile),
                        mortgage_value=tile.price // 2,
                    )
                )
            if tile.owner == player.id and tile.mortgaged:
                choices.append(
                    UnmortgagePropertyChoice(
                        player_id=player.id,
                        property_position=game.board.tiles.index(tile),
                        mortgage_value=int(tile.price * 0.55),
                    )
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
