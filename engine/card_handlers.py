from functools import singledispatch

from engine.game import Game, TurnPhase, build_available_choices
from engine.pending_payment import PendingPayment
from engine.cards import (
    Card,
    MoveStepsCard,
    MoveToPositionCard,
    MoneyCard,
    GoToJailCard,
    GetOutOfJailFreeCard,
    MoveToNearestTileByTypeCard,
    PayEachPlayerCard,
    CollectFromEachPlayerCard,
    PayPerImprovementCard,
)
from engine.events import (
    Event,
    PlayerPaidMoney,
    MoveReason,
)
from engine.choices import Choice
from engine.tiles import StreetTile


@singledispatch
def resolve_card(card: Card, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    raise NotImplementedError(f"No handler for card type {type(card)}")


@resolve_card.register
def _(card: MoveStepsCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    game.board.get_tile(player.position).deck.discard_card(card)
    return game.move_current_player_and_resolve_tile(
        steps=card.steps, reason=MoveReason.CARD
    )


@resolve_card.register
def _(card: MoveToPositionCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    game.board.get_tile(player.position).deck.discard_card(card)
    steps_forward = (card.position - player.position) % game.board.size()
    return game.move_current_player_and_resolve_tile(
        steps=steps_forward, reason=MoveReason.CARD
    )


@resolve_card.register
def _(card: MoneyCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)
    if card.amount < 0 and player.balance < -card.amount:
        game.pending_payment = PendingPayment(
            debtor_player_id=player.id,
            creditor_player_id=None,
            amount=-card.amount,
            reason="card",
        )
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, build_available_choices(game)
    player.update_balance(card.amount)
    events.append(
        PlayerPaidMoney(player_id=player.id, amount=card.amount, reason="card")
    )
    return game, events, choices


@resolve_card.register
def _(card: GoToJailCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    game.board.get_tile(player.position).deck.discard_card(card)
    events = game.send_player_to_jail(player, reason=MoveReason.TILE_EFFECT)
    return game, events, []


@resolve_card.register
def _(card: GetOutOfJailFreeCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []

    player.cards.append(card)

    return game, events, choices


@resolve_card.register
def _(card: MoveToNearestTileByTypeCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    game.board.get_tile(player.position).deck.discard_card(card)

    candidates = [
        pos for pos, tile in enumerate(game.board.tiles)
        if isinstance(tile, card.tile_type) and pos != player.position
    ]
    if not candidates:
        raise ValueError(f"No tile of type {card.tile_type} found on board")
    nearest_position = min(
        candidates,
        key=lambda pos: (pos - player.position) % game.board.size()
    )
    
    
    
    from_position = player.position
    steps_forward = (nearest_position - from_position) % game.board.size()
    steps_backward = (from_position - nearest_position) % game.board.size()
    steps = steps_forward if steps_forward <= steps_backward else -steps_backward
    return game.move_current_player_and_resolve_tile(steps=steps, reason=MoveReason.CARD)


@resolve_card.register
def _(card: PayEachPlayerCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)
    payee_ids = game.active_player_ids(exclude_ids={player.id})
    total_payment = card.amount * len(payee_ids)
    if total_payment > 0 and player.balance < total_payment:
        game.pending_payment = PendingPayment(
            debtor_player_id=player.id,
            creditor_player_id=None,
            amount=total_payment,
            reason="card_pay_each_player",
            per_player_amount=card.amount,
            remaining_player_ids=payee_ids,
        )
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, build_available_choices(game)

    events.extend(
        game.pay_each_player(
            payer_id=player.id, amount=card.amount, payee_ids=payee_ids
        )
    )

    return game, events, choices

@resolve_card.register
def _(card: CollectFromEachPlayerCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    game.board.get_tile(player.position).deck.discard_card(card)
    payer_ids = game.active_player_ids(exclude_ids={player.id})
    return game.collect_from_each_player(
        payee_id=player.id,
        payer_ids=payer_ids,
        amount=card.amount,
        end_turn=False,
    )

@resolve_card.register
def _(card: PayPerImprovementCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)

    total_payment = 0
    for tile in game.board.tiles:
        if isinstance(tile, StreetTile) and tile.owner == player.id:
            level = min(tile.improvement_level, len(card.amount) - 1)
            payment = card.amount[level]
            total_payment += payment

    if total_payment > 0 and player.balance < total_payment:
        game.pending_payment = PendingPayment(
            debtor_player_id=player.id,
            creditor_player_id=None,
            amount=total_payment,
            reason="card_pay_per_improvement",
        )
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, build_available_choices(game)

    player.update_balance(-total_payment)
    events.append(
        PlayerPaidMoney(
            player_id=player.id,
            amount=-total_payment,
            reason="card_pay_per_improvement",
        )
    )

    return game, events, choices