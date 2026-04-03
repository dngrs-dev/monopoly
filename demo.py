import random

from board import Board
from dice import Dice
from game import Game, TurnPhase, apply_command, end_turn, start_game
from player import Player
from choices import (
    BuyPropertyChoice,
    DeclineBuyPropertyChoice,
    RollDiceChoice,
    PayFineChoice,
    TryDoublesJailChoice,
)
from tiles import TileType, StartTile, PropertyTile, MoveTile, JailTile, ChanceTile


def build_demo_board() -> Board:
    tiles = [
        StartTile(name="Start", tile_type=TileType.START, go_bonus=200, stay_bonus=100),
        PropertyTile(
            name="Mediterranean Ave", tile_type=TileType.PROPERTY, price=60, rent=2
        ),
        ChanceTile(name="Chance", tile_type=TileType.CHANCE),
        PropertyTile(name="Baltic Ave", tile_type=TileType.PROPERTY, price=60, rent=4),
        MoveTile(name="Go To Start", tile_type=TileType.MOVE, move_to=0),
        PropertyTile(
            name="Reading Railroad", tile_type=TileType.PROPERTY, price=200, rent=25
        ),
        JailTile(name="Jail", tile_type=TileType.JAIL, skips=1),
        PropertyTile(
            name="Oriental Ave", tile_type=TileType.PROPERTY, price=100, rent=6
        ),
    ]
    return Board(tiles=tiles)


def print_events(events: list[object]) -> None:
    for e in events:
        print(f"  - {e}")


def print_choices(choices: list[object]) -> None:
    for c in choices:
        print(f"  - {c}")


def main() -> None:
    random.seed(1234)

    board = build_demo_board()
    game = Game(
        board=board,
        players=[Player(id=1, balance=500), Player(id=2, balance=500)],
        dice=Dice(),
    )

    game, events, choices = start_game(game)

    turns = 12
    for turn in range(1, turns + 1):
        player = game.current_player()
        print(
            f"\nTurn {turn} | Player {player.id} | balance={player.balance} pos={player.position} | skip_turns={player.skip_turns}"
        )
        print(f"Current phase: {game.turn_phase}")

        while choices:
            choice = choices[0]
            print(f"{choice=}")
            if isinstance(choice, RollDiceChoice):
                game, ev2, choices = apply_command(game, choice)
                events.extend(ev2)
            if isinstance(choice, BuyPropertyChoice):
                game, ev2, choices = apply_command(game, choice)
                events.extend(ev2)
            if isinstance(choice, DeclineBuyPropertyChoice):
                game, ev2, choices = apply_command(game, choice)
                events.extend(ev2)
            if isinstance(choice, PayFineChoice):
                game, ev2, choices = apply_command(game, choice)
                events.extend(ev2)
            if isinstance(choice, TryDoublesJailChoice):
                game, ev2, choices = apply_command(game, choice)
                events.extend(ev2)

        print_events(events)
        # print_choices(choices)

        if game.turn_phase == TurnPhase.END_TURN:
            print("Ending turn...")
            game, events, choices = end_turn(game)

    print("\nFinal state:")
    for p in game.players:
        print(
            f"Player {p.id}: balance={p.balance} position={p.position} skip_turns={p.skip_turns}"
        )


if __name__ == "__main__":
    main()
