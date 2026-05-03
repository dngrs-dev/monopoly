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
    PlayerMoved,
    PlayerPaidMoney,
    PlayerWentToJail,
    MoveReason,
)
from engine.choices import Choice
from engine.tiles import JailTile, StreetTile
from engine.tile_handlers import resolve_tile


@singledispatch
def resolve_card(card: Card, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    raise NotImplementedError(f"No handler for card type {type(card)}")


@resolve_card.register
def _(card: MoveStepsCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)
    from_position = player.position
    move_events = player.move_steps(card.steps, game.board)
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            steps=card.steps,
            reason=MoveReason.CARD,
        )
    )
    events.extend(move_events)
    game, tile_events, tile_choices = resolve_tile(
        game.board.get_tile(player.position), game
    )
    events.extend(tile_events)
    choices.extend(tile_choices)
    return game, events, choices


@resolve_card.register
def _(card: MoveToPositionCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)
    from_position = player.position
    steps_forward = (card.position - from_position) % game.board.size()
    move_events = player.move_position(card.position, game.board)
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            steps=steps_forward,
            reason=MoveReason.CARD,
        )
    )
    events.extend(move_events)
    game, tile_events, tile_choices = resolve_tile(
        game.board.get_tile(player.position), game
    )
    events.extend(tile_events)
    choices.extend(tile_choices)
    return game, events, choices


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
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)

    # Move player to jail
    from_position = player.position
    jail_position = next(
        (i for i, t in enumerate(game.board.tiles) if isinstance(t, JailTile)), None
    )
    if jail_position is None:
        raise ValueError("Board does not have a Jail tile")
    player.position = jail_position
    player.in_jail = True
    player.skip_turns = game.board.get_tile(jail_position).skip_turns
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            reason=MoveReason.TILE_EFFECT,
        )
    )
    events.append(PlayerWentToJail(player_id=player.id))
    return game, events, choices


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
    events: list[Event] = []
    choices: list[Choice] = []
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
    move_events = player.move_steps(steps, game.board)
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            steps=steps,
            reason=MoveReason.CARD,
        )
    )
    events.extend(move_events)
    game, tile_events, tile_choices = resolve_tile(
        game.board.get_tile(player.position), game
    )
    events.extend(tile_events)
    choices.extend(tile_choices)
    return game, events, choices


@resolve_card.register
def _(card: PayEachPlayerCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)
    other_players = [p for p in game.players if p.id != player.id]
    total_payment = card.amount * len(other_players)
    if total_payment > 0 and player.balance < total_payment:
        game.pending_payment = PendingPayment(
            debtor_player_id=player.id,
            creditor_player_id=None,
            amount=total_payment,
            reason="card_pay_each_player",
            per_player_amount=card.amount,
        )
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, build_available_choices(game)

    for other_player in other_players:
        other_player.update_balance(card.amount)
        player.update_balance(-card.amount)
        events.append(
            PlayerPaidMoney(
                player_id=player.id,
                amount=-card.amount,
                reason="card_pay_each_player",
            )
        )
        events.append(
            PlayerPaidMoney(
                player_id=other_player.id,
                amount=card.amount,
                reason="card_receive_from_each_player",
            )
        )

    return game, events, choices

@resolve_card.register
def _(card: CollectFromEachPlayerCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    game.board.get_tile(player.position).deck.discard_card(card)
    payer_ids = [p.id for p in game.players if p.id != player.id]
    for index, payer_id in enumerate(payer_ids):
        other_player = next((p for p in game.players if p.id == payer_id), None)
        if other_player is None:
            raise ValueError("Player not found")
        if other_player.balance < card.amount:
            game.pending_payment = PendingPayment(
                debtor_player_id=other_player.id,
                creditor_player_id=player.id,
                amount=card.amount,
                reason="card_collect_from_each_player",
                per_player_amount=card.amount,
                remaining_player_ids=payer_ids[index + 1 :],
            )
            game.turn_phase = TurnPhase.AWAIT_CHOICE
            return game, events, build_available_choices(game)

        other_player.update_balance(-card.amount)
        player.update_balance(card.amount)
        events.append(
            PlayerPaidMoney(
                player_id=other_player.id,
                amount=-card.amount,
                reason="card_pay_each_player",
            )
        )
        events.append(
            PlayerPaidMoney(
                player_id=player.id,
                amount=card.amount,
                reason="card_receive_from_each_player",
            )
        )

    return game, events, choices

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