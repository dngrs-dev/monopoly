from dataclasses import dataclass
from enum import Enum, auto

from board import Board
from player import Player
from dice import Dice
from events import (
    Event,
    PlayerLanded,
    PlayerPassedStart,
    PlayerBoughtProperty,
    PlayerPaidRent,
    PlayerWentToJail,
    PlayerMoved,
    PlayerSkipTurn,
    PlayerPaidJailFine,
    PlayerRolledDice,
)
from choices import (
    Choice,
    BuyPropertyChoice,
    PayFineChoice,
    TryDoublesJailChoice,
    DeclineBuyPropertyChoice,
    RollDiceChoice,
)
from tiles import PropertyTile, JailTile, MoveTile, StartTile, ChanceTile


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

    def current_player(self) -> Player:
        return self.players[self.current_player_index]


def start_game(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    choices = [RollDiceChoice(player_id=game.current_player().id)]
    return game, [], choices


def end_turn(game: Game) -> tuple[Game, list[Event], list[Choice]]:
    game.current_player_index = (game.current_player_index + 1) % len(game.players)
    game.turn_phase = TurnPhase.AWAIT_CHOICE
    if game.current_player().in_jail:
        choices = [
            PayFineChoice(player_id=game.current_player().id, fine=50),
            TryDoublesJailChoice(player_id=game.current_player().id),
        ]
    else:
        choices = [RollDiceChoice(player_id=game.current_player().id)]
    return game, [], choices


def resolve_tile(
    game: Game, max_chain: int = 10
) -> tuple[Game, list[Event], list[Choice]]:
    player = game.current_player()
    tile = game.board.get_tile(player.position)

    events: list[Event] = []
    choices: list = []

    events.append(
        PlayerLanded(player_id=player.id, position=player.position, tile_name=tile.name)
    )

    for _ in range(max_chain):
        if isinstance(tile, PropertyTile):
            if tile.owner is None:
                if player.balance < tile.price:
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

            player.balance -= tile.rent
            owner = next((p for p in game.players if p.id == tile.owner), None)
            if owner is not None:
                owner.balance += tile.rent
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
        elif isinstance(tile, MoveTile):
            from_position = player.position
            player.position = tile.move_to
            events.append(
                PlayerMoved(
                    player_id=player.id,
                    from_position=from_position,
                    to_position=player.position,
                    reason=f"Move tile: {tile.name}",
                )
            )
            tile = game.board.get_tile(player.position)
            continue
        elif isinstance(tile, JailTile):
            player.in_jail = True
            player.skip_turns += tile.skips
            events.append(PlayerWentToJail(player_id=player.id))
        elif isinstance(tile, ChanceTile):
            pass
        elif isinstance(tile, StartTile):
            player.balance += tile.stay_bonus
            events.append(PlayerPassedStart(player_id=player.id))
        else:
            raise TypeError(f"Unknown tile type: {type(tile)}")

        game.turn_phase = TurnPhase.END_TURN
        return game, events, choices


def apply_command(game: Game, choice: Choice) -> tuple[Game, list[Event], list[Choice]]:
    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if choice.player_id != player.id:
        raise ValueError("It's not this player's turn")

    if isinstance(choice, RollDiceChoice):
        if game.turn_phase != TurnPhase.AWAIT_CHOICE:
            raise ValueError("Cannot roll dice at this phase")

        if player.skip_turns > 0:
            player.skip_turns -= 1
            game.turn_phase = TurnPhase.END_TURN
            events.append(
                PlayerSkipTurn(player_id=player.id, turns_left=player.skip_turns)
            )
            return game, events, choices

        dice1, dice2 = game.dice.roll_two()
        roll = dice1 + dice2
        from_position = player.position
        player.move(roll, len(game.board.tiles))

        events.append(PlayerRolledDice(player_id=player.id, dice1=dice1, dice2=dice2))
        events.append(
            PlayerMoved(
                player_id=player.id,
                from_position=from_position,
                to_position=player.position,
                steps=roll,
                reason=f"Rolled a {roll}",
            )
        )

        game.turn_phase = TurnPhase.RESOLVE_TILE
        game, tile_events, tile_choices = resolve_tile(game)
        events.extend(tile_events)
        choices.extend(tile_choices)
        return game, events, choices

    if isinstance(choice, BuyPropertyChoice):
        if game.turn_phase != TurnPhase.AWAIT_CHOICE:
            raise ValueError("Cannot buy property at this phase")
        tile = game.board.get_tile(player.position)
        if not isinstance(tile, PropertyTile):
            raise ValueError("Current tile is not a property")
        if tile.name != choice.property_name:
            raise ValueError("Property name does not match current tile")
        if tile.owner is not None:
            raise ValueError("Property is already owned")
        if player.balance < tile.price:
            raise ValueError("Player cannot afford this property")

        player.balance -= tile.price
        tile.owner = player.id
        events.append(
            PlayerBoughtProperty(
                player_id=player.id, property_name=tile.name, price=tile.price
            )
        )
        game.turn_phase = TurnPhase.END_TURN
        return game, events, choices

    if isinstance(choice, PayFineChoice):
        if game.turn_phase != TurnPhase.AWAIT_CHOICE:
            raise ValueError("Cannot pay fine at this phase")
        tile = game.board.get_tile(player.position)
        if not isinstance(tile, JailTile):
            raise ValueError("Current tile is not a jail")
        if player.balance < tile.fine:
            raise ValueError("Player cannot afford the fine")

        player.balance -= tile.fine
        player.in_jail = False
        player.skip_turns = 0
        events.append(PlayerPaidJailFine(player_id=player.id, amount=tile.fine))
        game.turn_phase = TurnPhase.AWAIT_CHOICE
        choices.append(RollDiceChoice(player_id=player.id))
        return game, events, choices

    if isinstance(choice, TryDoublesJailChoice):
        if game.turn_phase != TurnPhase.AWAIT_CHOICE:
            raise ValueError("Cannot try doubles at this phase")
        tile = game.board.get_tile(player.position)
        if not isinstance(tile, JailTile):
            raise ValueError("Current tile is not a jail")

        dice1, dice2 = game.dice.roll_two()
        events.append(PlayerRolledDice(player_id=player.id, dice1=dice1, dice2=dice2))
        if dice1 == dice2:
            player.in_jail = False
            player.skip_turns = 0
            game.turn_phase = TurnPhase.RESOLVE_TILE
        else:
            player.skip_turns -= 1
            game.turn_phase = TurnPhase.END_TURN
        return game, events, choices

    raise ValueError("Unknown command type")
