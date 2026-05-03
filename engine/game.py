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
    PayPendingPaymentChoice,
    DeclareBankruptcyChoice,
)
from engine.cards import GetOutOfJailFreeCard
from engine.tiles import JailTile, StreetTile, OwnableTile
from engine.rules import Rules
from engine.auction import Auction
from engine.tradeoffer import TradeOffer
from engine.pending_payment import PendingPayment


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
    doubles_in_row: int = 0
    pending_extra_turn: bool = False
    turn_phase: TurnPhase = TurnPhase.AWAIT_CHOICE
    rules: Rules = field(default_factory=Rules)
    auction: Auction | None = None
    trade_offer: TradeOffer | None = None
    pending_payment: PendingPayment | None = None

    def current_player(self) -> Player:
        return self.players[self.current_player_index]


def _build_asset_management_choices(
    game: Game,
    *,
    player: Player,
    include_buy_improvements: bool,
    include_sell_improvements: bool,
    include_mortgage: bool,
    include_unmortgage: bool,
) -> list[Choice]:
    choices: list[Choice] = []

    for pos, tile in enumerate(game.board.tiles):
        if isinstance(tile, StreetTile) and tile.owner == player.id:
            group_tiles = game.board.get_group_tiles(tile.group_id)
            owns_monopoly = all(t.owner == player.id for t in group_tiles)

            if include_buy_improvements and owns_monopoly:
                if tile.improvement_level < len(tile.rent_schedule) - 1:
                    improvement_price = (
                        tile.improvement_prices
                        if isinstance(tile.improvement_prices, int)
                        else tile.improvement_prices[tile.improvement_level]
                    )
                    choices.append(
                        BuyImprovementChoice(
                            player_id=player.id,
                            property_position=pos,
                            price=improvement_price,
                        )
                    )

            if include_sell_improvements:
                if tile.improvement_level > 0:
                    last_improvement_price = (
                        tile.improvement_prices
                        if isinstance(tile.improvement_prices, int)
                        else tile.improvement_prices[tile.improvement_level - 1]
                    )
                    improvement_sell_price = int(
                        last_improvement_price * tile.improvement_sell_price_multiplier
                    )
                    choices.append(
                        SellImprovementChoice(
                            player_id=player.id,
                            property_position=pos,
                            price=improvement_sell_price,
                        )
                    )

        if not isinstance(tile, OwnableTile):
            continue

        if isinstance(tile, StreetTile) and tile.improvement_level > 0:
            continue  # Can't mortgage if there are improvements

        if tile.owner != player.id:
            continue

        if include_mortgage and not tile.mortgaged:
            choices.append(
                MortgagePropertyChoice(
                    player_id=player.id,
                    property_position=pos,
                    mortgage_value=tile.price // 2,
                )
            )

        if include_unmortgage and tile.mortgaged:
            choices.append(
                UnmortgagePropertyChoice(
                    player_id=player.id,
                    property_position=pos,
                    unmortgage_value=int(tile.price * 0.55),
                )
            )

    return choices


def _build_turn_choices(game: Game) -> list[Choice]:
    player = game.current_player()

    if player.in_jail:
        tile = game.board.get_tile(player.position)
        if not isinstance(tile, JailTile):
            raise ValueError("Player is in jail but not on a JailTile")
        choices: list[Choice] = [
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

    choices.extend(
        _build_asset_management_choices(
            game,
            player=player,
            include_buy_improvements=True,
            include_sell_improvements=True,
            include_mortgage=True,
            include_unmortgage=True,
        )
    )

    return choices


def _build_pending_payment_choices(game: Game) -> list[Choice]:
    pending = game.pending_payment
    if pending is None:
        raise ValueError("No pending payment")

    player = next((p for p in game.players if p.id == pending.debtor_player_id), None)
    if player is None:
        raise ValueError("Pending payment debtor not found")

    choices: list[Choice] = []
    choices.extend(
        _build_asset_management_choices(
            game,
            player=player,
            include_buy_improvements=False,
            include_sell_improvements=True,
            include_mortgage=True,
            include_unmortgage=False,
        )
    )

    if player.balance >= pending.amount:
        choices.append(
            PayPendingPaymentChoice(
                player_id=player.id,
                amount=pending.amount,
                to_player_id=pending.creditor_player_id,
                reason=pending.reason,
            )
        )

    choices.append(DeclareBankruptcyChoice(player_id=player.id))
    return choices


def build_available_choices(game: Game) -> list[Choice]:
    if game.pending_payment is not None:
        return _build_pending_payment_choices(game)
    return _build_turn_choices(game)


def start_game(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    return game, [], build_available_choices(game)


def end_turn(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    # Advance to the next non-bankrupt player.
    if not game.pending_extra_turn:
        game.doubles_in_row = 0
        for _ in range(len(game.players)):
            game.current_player_index = (game.current_player_index + 1) % len(game.players)
            if not game.current_player().bankrupt:
                break
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    return game, [], build_available_choices(game)


def apply_command(game: Game, choice: Choice) -> tuple[Game, list[Event], list[Choice]]:
    from engine.choice_handlers import apply_choice

    return apply_choice(choice, game)
