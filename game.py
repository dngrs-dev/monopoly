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
)
from choices import Choice, BuyPropertyChoice
from commands import Command, RollDiceCommand
from tiles import Tile, PropertyTile, JailTile, MoveTile, StartTile, ChanceTile


class TurnPhase(Enum):
    AWAIT_ROLL = auto()
    RESOLVE_TILE = auto()
    AWAIT_CHOICE = auto()
    END_TURN = auto()


@dataclass
class Game:
    board: Board
    players: list[Player]
    dice: Dice
    current_player_index: int = 0
    turn_phase: TurnPhase = TurnPhase.AWAIT_ROLL

    def current_player(self) -> Player:
        return self.players[self.current_player_index]


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
                game.turn_phase = TurnPhase.AWAIT_CHOICE
                return game, events, choices
            if tile.owner == player.id:
                game.turn_phase = TurnPhase.END_TURN
                return game, events, choices

            player.balance -= tile.rent
            owner = next(p for p in game.players if p.id == tile.owner)
            if owner:
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
            continue
        elif isinstance(tile, JailTile):
            pass
        elif isinstance(tile, ChanceTile):
            pass
        elif isinstance(tile, StartTile):
            player.balance += tile.stay_bonus
            events.append(PlayerPassedStart(player_id=player.id))
        else:
            raise TypeError(f"Unknown tile type: {type(tile)}")

        game.turn_phase = TurnPhase.END_TURN
        return game, events, choices


def apply_command(
    game: Game, command: Command | Choice
) -> tuple[Game, list[Event], list[Choice]]:
    events: list[Event] = []
    choices: list[Choice] = []

    player = game.current_player()
    if command.player_id != player.id:
        raise ValueError("It's not this player's turn")

    if isinstance(command, RollDiceCommand):
        if game.turn_phase != TurnPhase.AWAIT_ROLL:
            raise ValueError("Cannot roll dice at this phase")

        if player.skip_turns > 0:
            player.skip_turns -= 1
            game.turn_phase = TurnPhase.END_TURN
            events.append(
                PlayerSkipTurn(player_id=player.id, turns_left=player.skip_turns)
            )
            return game, events, choices

        roll = game.dice.roll()
        from_position = player.position
        player.move(roll, len(game.board.tiles))

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

    if isinstance(command, BuyPropertyChoice):
        if game.turn_phase != TurnPhase.AWAIT_CHOICE:
            raise ValueError("Cannot buy property at this phase")
        tile = game.board.get_tile(player.position)
        if not isinstance(tile, PropertyTile):
            raise ValueError("Current tile is not a property")
        if tile.name != command.property_name:
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
    
    raise ValueError("Unknown command type")
