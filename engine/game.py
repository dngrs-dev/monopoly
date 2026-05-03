from dataclasses import dataclass, field
from enum import Enum, auto

from engine.board import Board
from engine.player import Player
from engine.dice import Dice
from engine.events import Event, MoveReason, PlayerMoved, PlayerPaidMoney, PlayerWentToJail
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

    def get_player(self, player_id: int) -> Player:
        player = next((p for p in self.players if p.id == player_id), None)
        if player is None:
            raise ValueError("Player not found")
        return player

    def active_players(self, *, exclude_ids: set[int] | None = None) -> list[Player]:
        exclude = exclude_ids or set()
        return [p for p in self.players if not p.bankrupt and p.id not in exclude]

    def active_player_ids(self, *, exclude_ids: set[int] | None = None) -> list[int]:
        return [p.id for p in self.active_players(exclude_ids=exclude_ids)]

    def send_player_to_jail(self, player: Player, *, reason: MoveReason) -> list[Event]:
        from_position = player.position
        jail_position = self.board.find_tile_position(JailTile)
        player.position = jail_position
        player.in_jail = True
        player.skip_turns = self.board.get_tile(jail_position).skip_turns
        return [
            PlayerMoved(
                player_id=player.id,
                from_position=from_position,
                to_position=player.position,
                reason=reason,
            ),
            PlayerWentToJail(player_id=player.id),
        ]

    def move_current_player_and_resolve_tile(
        self,
        *,
        steps: int,
        reason: MoveReason,
    ) -> tuple["Game", list[Event], list[Choice]]:
        from engine.tile_handlers import resolve_tile

        events: list[Event] = []
        player = self.current_player()
        from_position = player.position
        move_events = player.move_steps(steps, self.board)
        events.append(
            PlayerMoved(
                player_id=player.id,
                from_position=from_position,
                to_position=player.position,
                steps=steps,
                reason=reason,
            )
        )
        events.extend(move_events)
        game, tile_events, tile_choices = resolve_tile(
            self.board.get_tile(player.position), self
        )
        events.extend(tile_events)
        return game, events, tile_choices

    def pay_each_player(
        self,
        *,
        payer_id: int,
        amount: int,
        payee_ids: list[int] | None = None,
    ) -> list[Event]:
        payer = self.get_player(payer_id)
        if payee_ids is None:
            payee_ids = self.active_player_ids(exclude_ids={payer_id})
        else:
            payee_ids = [
                player_id
                for player_id in payee_ids
                if player_id != payer_id and not self.get_player(player_id).bankrupt
            ]

        events: list[Event] = []
        for payee_id in payee_ids:
            payee = self.get_player(payee_id)
            payer.update_balance(-amount)
            payee.update_balance(amount)
            events.append(
                PlayerPaidMoney(
                    player_id=payer_id,
                    amount=-amount,
                    reason="card_pay_each_player",
                )
            )
            events.append(
                PlayerPaidMoney(
                    player_id=payee_id,
                    amount=amount,
                    reason="card_receive_from_each_player",
                )
            )

        return events

    def collect_from_each_player(
        self,
        *,
        payee_id: int,
        payer_ids: list[int],
        amount: int,
        end_turn: bool,
    ) -> tuple["Game", list[Event], list[Choice]]:
        events: list[Event] = []
        choices: list[Choice] = []
        payee = self.get_player(payee_id)

        filtered_payer_ids = [
            payer_id
            for payer_id in payer_ids
            if not self.get_player(payer_id).bankrupt
        ]

        for index, payer_id in enumerate(filtered_payer_ids):
            payer = self.get_player(payer_id)
            if payer.balance < amount:
                self.pending_payment = PendingPayment(
                    debtor_player_id=payer_id,
                    creditor_player_id=payee_id,
                    amount=amount,
                    reason="card_collect_from_each_player",
                    per_player_amount=amount,
                    remaining_player_ids=filtered_payer_ids[index + 1 :],
                )
                self.turn_phase = TurnPhase.AWAIT_CHOICE
                return self, events, build_available_choices(self)

            payer.update_balance(-amount)
            payee.update_balance(amount)
            events.append(
                PlayerPaidMoney(
                    player_id=payer_id,
                    amount=-amount,
                    reason="card_pay_each_player",
                )
            )
            events.append(
                PlayerPaidMoney(
                    player_id=payee_id,
                    amount=amount,
                    reason="card_receive_from_each_player",
                )
            )

        self.pending_payment = None
        if end_turn:
            self.turn_phase = TurnPhase.END_TURN
        return self, events, choices


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
                    improvement_price = tile.improvement_buy_price()
                    choices.append(
                        BuyImprovementChoice(
                            player_id=player.id,
                            property_position=pos,
                            price=improvement_price,
                        )
                    )

            if include_sell_improvements:
                if tile.improvement_level > 0:
                    improvement_sell_price = tile.improvement_sell_price()
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
                    mortgage_value=tile.mortgage_value(),
                )
            )

        if include_unmortgage and tile.mortgaged:
            choices.append(
                UnmortgagePropertyChoice(
                    player_id=player.id,
                    property_position=pos,
                    unmortgage_value=tile.unmortgage_value(),
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

    for p in game.active_players(exclude_ids={player.id}):
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

    player = game.get_player(pending.debtor_player_id)

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
