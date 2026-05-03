from functools import singledispatch
from engine.tiles import (
    Tile,
    StartTile,
    OwnableTile,
    ChanceTile,
    GoToJailTile,
    StreetTile,
    RailroadTile,
    UtilityTile,
    NoneTile,
    PayTile,
)
from engine.game import Game, TurnPhase, PendingPayment, build_available_choices
from engine.events import (
    Event,
    PlayerLanded,
    PlayerPaidRent,
    PlayerDrewCard,
    MoveReason,
    PlayerPaidFine,
)
from engine.choices import Choice, BuyPropertyChoice, DeclineBuyPropertyChoice
from engine.player import Player
from engine.cards import GetOutOfJailFreeCard


def _landing_event(player: Player, tile: Tile) -> PlayerLanded:
    return PlayerLanded(
        player_id=player.id, position=player.position
    )


@singledispatch
def resolve_tile(
    tile: Tile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    raise NotImplementedError(f"No handler for tile type: {type(tile)}")


@resolve_tile.register
def _(
    tile: OwnableTile, game: Game, max_chain: int = 10
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
                player_id=player.id, property_position=game.board.get_tile_position(tile), price=tile.price
            )
        )
        choices.append(DeclineBuyPropertyChoice(player_id=player.id))
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, choices
    if tile.owner == player.id:
        game.turn_phase = TurnPhase.END_TURN
        return game, events, choices

    # Pay rent
    if tile.mortgaged:
        game.turn_phase = TurnPhase.END_TURN
        return game, events, choices
    tile.rent = _calculate_rent(tile, game)  # Update tile with fresh rent

    if player.balance < tile.rent:
        game.pending_payment = PendingPayment(
            debtor_player_id=player.id,
            creditor_player_id=tile.owner,
            amount=tile.rent,
            reason="rent",
            property_position=game.board.get_tile_position(tile),
        )
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, build_available_choices(game)

    player.update_balance(-tile.rent)
    owner = next((p for p in game.players if p.id == tile.owner), None)
    if owner is not None:
        owner.update_balance(tile.rent)
    events.append(
        PlayerPaidRent(
            player_id=player.id,
            to_player_id=tile.owner,
            property_position=game.board.get_tile_position(tile),
            rent=tile.rent,
        )
    )

    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


def _calculate_rent(tile: OwnableTile, game: Game) -> int:
    if isinstance(tile, StreetTile):
        rent = tile.rent_schedule[tile.improvement_level]
        if game.rules.double_rent_on_monopoly:
            group_tiles = game.board.get_group_tiles(tile.group_id)
            if tile.improvement_level == 0 and all(
                t.owner == tile.owner for t in group_tiles
            ):
                rent *= 2
        return rent
    elif isinstance(tile, RailroadTile):
        group_tiles = game.board.get_group_tiles(tile.group_id)
        owned_count = sum(1 for t in group_tiles if t.owner == tile.owner)
        return tile.rent_schedule[owned_count - 1] if owned_count > 0 else 0
    elif isinstance(tile, UtilityTile):
        utilities = [t for t in game.board.get_group_tiles(tile.group_id) if isinstance(t, UtilityTile)]
        owned_count = sum(1 for t in utilities if t.owner == tile.owner)
        multiplier = tile.rent_multiplier[min(owned_count - 1, len(tile.rent_multiplier) - 1)] if owned_count > 0 else 0
        return multiplier * game.dice.last_roll
    else:
        return tile.rent


@resolve_tile.register
def _(
    tile: StartTile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    # Passing or landing on start are handled in player movement logic, so just end turn here

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
    events.extend(game.send_player_to_jail(player, reason=MoveReason.TILE_EFFECT))

    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@resolve_tile.register
def _(
    tile: ChanceTile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    # Draw a card and resolve it
    card = tile.deck.draw_card()
    if isinstance(card, GetOutOfJailFreeCard):
        card.origin_deck = tile.deck
    events.append(PlayerDrewCard(player_id=player.id, card_name=type(card).__name__))
    from engine.card_handlers import resolve_card

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


@resolve_tile.register
def _(
    tile: NoneTile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    # Just end turn, no action
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@resolve_tile.register
def _(
    tile: PayTile, game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    events: list[Event] = [_landing_event(player, tile)]
    choices: list[Choice] = []

    if player.balance < tile.amount:
        game.pending_payment = PendingPayment(
            debtor_player_id=player.id,
            creditor_player_id=None,
            amount=tile.amount,
            reason="fine",
            property_position=game.board.get_tile_position(tile),
        )
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        return game, events, build_available_choices(game)

    # Pay the specified amount
    player.update_balance(-tile.amount)
    events.append(PlayerPaidFine(player_id=player.id, amount=tile.amount))

    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices
