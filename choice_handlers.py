from functools import singledispatch
from choices import *
from game import Game, TurnPhase
from events import *
from tiles import *
from tile_handlers import resolve_tile
from cards import *


def _assert_turn(game: Game, player_id: int):
    if game.current_player().id != player_id:
        raise ValueError("It's not the player's turn")
    if game.turn_phase != TurnPhase.AWAIT_CHOICE:
        raise ValueError("Not awaiting choice")


@singledispatch
def apply_choice(choice: Choice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    raise NotImplementedError(f"No handler for choice type: {type(choice)}")


@apply_choice.register
def _(choice: RollDiceChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if player.in_jail:
        raise ValueError("Player is in jail and cannot roll dice")

    dice1, dice2 = game.dice.roll()
    roll = dice1 + dice2
    from_position = player.position
    move_events = player.move_steps(roll, game.board)

    events.append(PlayerRolledDice(player_id=player.id, dice1=dice1, dice2=dice2))
    events.append(
        PlayerMoved(
            player_id=player.id,
            from_position=from_position,
            to_position=player.position,
            steps=roll,
            reason=MoveReason.ROLL_DICE,
        )
    )
    events.extend(move_events)

    game.turn_phase = TurnPhase.RESOLVE_TILE
    game, tile_events, tile_choices = resolve_tile(
        game.board.get_tile(game.current_player().position), game
    )
    events.extend(tile_events)
    choices.extend(tile_choices)
    return game, events, choices


@apply_choice.register
def _(choice: BuyPropertyChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    tile = game.board.get_tile(player.position)
    if not isinstance(tile, PropertyTile):
        raise ValueError("Current tile is not a property")
    if tile.owner is not None:
        raise ValueError("Property is already owned")
    if player.balance < tile.price:
        raise ValueError("Player cannot afford this property")
    if tile.price != choice.price:
        raise ValueError("Offer price does not match property price")
    if tile.name != choice.property_name:
        raise ValueError("Property name does not match current tile")

    player.update_balance(-tile.price)
    tile.owner = player.id
    events.append(
        PlayerBoughtProperty(
            player_id=player.id, property_name=tile.name, price=tile.price
        )
    )
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@apply_choice.register
def _(
    choice: DeclineBuyPropertyChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    tile = game.board.get_tile(player.position)
    if not isinstance(tile, PropertyTile):
        raise ValueError("Current tile is not a property")
    if tile.owner is not None:
        raise ValueError("Property is already owned")

    # No events for declining to buy (could be added in future)
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@apply_choice.register
def _(choice: PayFineChoice, game: Game) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if not player.in_jail:
        raise ValueError("Player is not in jail")
    if player.balance < choice.fine:
        raise ValueError("Player cannot afford the fine")

    player.update_balance(-choice.fine)
    player.in_jail = False
    player.skip_turns = 0
    events.append(PlayerPaidJailFine(player_id=player.id, amount=choice.fine))
    events.append(PlayerReleasedFromJail(player_id=player.id))
    game.turn_phase = TurnPhase.END_TURN
    return game, events, choices


@apply_choice.register
def _(
    choice: TryDoublesJailChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if not player.in_jail:
        raise ValueError("Player is not in jail")

    dice1, dice2 = game.dice.roll()
    events.append(PlayerRolledDice(player_id=player.id, dice1=dice1, dice2=dice2))

    if dice1 == dice2:
        player.in_jail = False
        player.skip_turns = 0
        events.append(PlayerReleasedFromJail(player_id=player.id))
        # Move the player according to the roll
        from_position = player.position
        roll = dice1 + dice2
        move_events = player.move_steps(roll, game.board)
        events.append(
            PlayerMoved(
                player_id=player.id,
                from_position=from_position,
                to_position=player.position,
                steps=roll,
                reason=MoveReason.ROLL_DICE,
            )
        )
        events.extend(move_events)
        game.turn_phase = TurnPhase.RESOLVE_TILE
        game, tile_events, tile_choices = resolve_tile(
            game.board.get_tile(game.current_player().position), game
        )
        events.extend(tile_events)
        choices.extend(tile_choices)
    else:
        player.skip_turns -= 1
        events.append(PlayerSkipTurn(player_id=player.id, turns_left=player.skip_turns))
        if player.skip_turns <= 0:
            # Player must pay fine on next turn if they fail to roll doubles
            choices.append(PayFineChoice(player_id=player.id, fine=50))
        else:
            game.turn_phase = TurnPhase.END_TURN

    return game, events, choices



@apply_choice.register
def _(
    choice: UseGetOutOfJailFreeCardChoice, game: Game
) -> tuple[Game, list[Event], list[Choice]]:
    _assert_turn(game, choice.player_id)

    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if not player.in_jail:
        raise ValueError("Player is not in jail")

    card_index = next(
        (
            i
            for i, card in enumerate(player.cards)
            if isinstance(card, GetOutOfJailFreeCard)
        ),
        None,
    )
    if card_index is None:
        raise ValueError("Player does not have a Get Out of Jail Free card")

    # Remove the card from player's hand
    card = player.cards.pop(card_index)
    events.append(PlayerUsedGetOutOfJailFreeCard(player_id=player.id))

    player.in_jail = False
    player.skip_turns = 0

    choices.append(
        RollDiceChoice(player_id=player.id)
    )  # Allow player to roll immediately after using the card
    events.append(PlayerReleasedFromJail(player_id=player.id))

    return game, events, choices
