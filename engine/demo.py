import random
from engine.game import Game, start_game, end_turn, TurnPhase, apply_command
from engine.board import Board
from engine.dice import Dice
from engine.player import Player
from engine.tiles import StartTile, OwnableTile, ChanceTile, JailTile, GoToJailTile
from engine.deck import Deck
from engine.cards import (
    MoveStepsCard,
    MoveToPositionCard,
    MoneyCard,
    GoToJailCard,
    GetOutOfJailFreeCard,
)
from engine.choices import UseGetOutOfJailFreeCardChoice


def build_demo_deck() -> Deck:
    return Deck(
        cards=[
            MoveStepsCard(steps=3),
            MoveToPositionCard(position=5),
            MoneyCard(amount=100),
            GoToJailCard(),
            GetOutOfJailFreeCard(),
        ]
    )


def build_demo_board() -> Board:
    deck = build_demo_deck()
    return Board(
        tiles=[
            StartTile(name="Start"),
            OwnableTile(name="Mediterranean Avenue", price=60, rent=2),
            ChanceTile(name="Chance", deck=deck),
            OwnableTile(name="Baltic Avenue", price=60, rent=4),
            JailTile(name="Jail"),
            OwnableTile(name="Oriental Avenue", price=100, rent=6),
            GoToJailTile(name="Go To Jail"),
            OwnableTile(name="Vermont Avenue", price=100, rent=6),
        ]
    )


def print_list(title: str, items: list[object]) -> None:
    print(f"{title}:")
    for item in items:
        print(f"  - {item}")
    if not items:
        print("  (none)")


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
            f"\nTurn {turn} | Player {player.id} | balance={player.balance} pos={player.position} skip_turns={player.skip_turns}"
        )
        print(f"Current phase: {game.turn_phase}")
        print_list("Events", events)

        while game.turn_phase != TurnPhase.END_TURN:
            if not choices:
                break  # No choices available, end turn

            print_list("Available choices", choices)
            # Get the getoutofjailfree card choice if available, otherwise just take the first choice
            choice = next(
                (c for c in choices if isinstance(c, UseGetOutOfJailFreeCardChoice)),
                choices[0],
            )
            print(f"Applying choice: {choice}")
            game, events, choices = apply_command(game, choice)
            print_list("Events", events)

        if game.turn_phase == TurnPhase.END_TURN:
            print("Ending turn...")
            game, events, choices = end_turn(game)

    print("\nFinal state:")
    for player in game.players:
        print(
            f"Player {player.id}: balance={player.balance} position={player.position} skip_turns={player.skip_turns}"
        )

    for tile in game.board.tiles:
        print(f"Tile {tile.name}:")
        for attr, value in vars(tile).items():
            print(f"  {attr}: {value}")


if __name__ == "__main__":
    main()
