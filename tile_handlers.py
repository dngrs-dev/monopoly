from functools import singledispatch
from tiles import *
from game import Game, TurnPhase
from events import *
from choices import *
from player import Player


def _landing_event(player: Player, tile: Tile) -> PlayerLanded:
    return PlayerLanded(
        player_id=player.id, position=player.position, tile_name=tile.name
    )


@singledispatch
def resolve_tile(
    tile: Tile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    raise NotImplementedError(f"No handler for tile type: {type(tile)}")


@resolve_tile.register
def _(
    tile: PropertyTile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    if tile.owner is None:
        if player.balance < tile.price:
            # No money to buy, just end turn
            game.turn_phase = TurnPhase.END_TURN
            return game, events, choices
        choices.append(
            BuyPropertyChoice(
                player_id=player.id, property_name=tile.name, price=tile.price
            )
        )
        choices.append(DeclineBuyPropertyChoice(player_id=player.id))
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, choices
    if tile.owner == player.id:
        game.turn_phase = TurnPhase.END_TURN
        return game, events, choices

    # Pay rent
    player.update_balance(-tile.rent)
    owner = next((p for p in game.players if p.id == tile.owner), None)
    if owner is not None:
        owner.update_balance(tile.rent)
    events.append(
        PlayerPaidRent(
            player_id=player.id,
            to_player_id=tile.owner,
            property_name=tile.name,
            rent=tile.rent,
        )
    )
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@resolve_tile.register
def _(
    tile: StartTile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    # Give player the bonus for landing on or passing start
    if player.position == game.board.get_tile_position(tile):
        player.update_balance(tile.land_bonus)
        events.append(PlayerLandedOnStart(player_id=player.id, amount=tile.land_bonus))
    else:
        player.update_balance(tile.pass_bonus)
        events.append(PlayerPassedStart(player_id=player.id, amount=tile.pass_bonus))

    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@resolve_tile.register
def _(
    tile: GoToJailTile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
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

    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@resolve_tile.register
def _(tile: ChanceTile, game: Game, max_chain: int = 10) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    # Draw a card and resolve it
    print(f"{tile.deck=}")
    card = tile.deck.draw_card()
    events.append(PlayerDrewCard(player_id=player.id, card_name=type(card).__name__))
    from card_handlers import resolve_card

    game, card_events, card_choices = resolve_card(card, game)
    events.extend(card_events)
    choices.extend(card_choices)
    if card_choices:
        game.turn_phase = TurnPhase.AWAIT_CHOICE
    else:
        game.turn_phase = TurnPhase.END_TURN
    return game, events, choices

@resolve_tile.register
def _(
    tile: Tile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    # For other tile types, just end turn
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices
