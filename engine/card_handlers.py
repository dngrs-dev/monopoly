from functools import singledispatch

from engine.game import Game
from engine.cards import (
    Card,
    MoveStepsCard,
    MoveToPositionCard,
    MoneyCard,
    GoToJailCard,
    GetOutOfJailFreeCard,
    MoveToNearestTileByTypeCard,
)
from engine.events import (
    Event,
    PlayerMoved,
    PlayerPaidMoney,
    PlayerWentToJail,
    MoveReason,
)
from engine.choices import Choice
from engine.tiles import JailTile
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

    # Find nearest tile of the specified type
    nearest_position = None
    for tile_pos in range(0, game.board.size()):
        tile = game.board.get_tile(tile_pos)
        if isinstance(tile, card.tile_type):
            if tile is not None and tile_pos != player.position:
                nearest_position = min(
                    nearest_position, tile_pos, key=lambda pos: (pos - player.position) % game.board.size()
                )
    if nearest_position is None:
        player_tile = game.board.get_tile(player.position)
        if isinstance(player_tile, card.tile_type):
            nearest_position = player.position
        else:
            raise ValueError(f"No tile of type {card.tile_type} found on board")
        
    
    
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