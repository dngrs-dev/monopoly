from functools import singledispatch

from game import Game
from cards import *
from events import *
from choices import Choice
from tiles import *
from tile_handlers import resolve_tile


@singledispatch
def resolve_card(card: Card, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    raise NotImplementedError(f"No handler for card type {type(card)}")


@resolve_card.register
def _(card: MoveStepsCard, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = []
    choices: list[Choice] = []
    from_position = player.position
    player.move(card.steps, board_size=len(game.board.tiles))
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            steps=card.steps,
            reason=MoveReason.CARD,
        )
    )
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
    from_position = player.position
    player.position = card.position
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            reason=MoveReason.CARD,
        )
    )
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
    raise NotImplementedError("GetOutOfJailFreeCard is not implemented yet")
    return game, events, choices
