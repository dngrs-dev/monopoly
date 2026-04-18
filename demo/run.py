import random
from engine.game import Game, start_game, end_turn, TurnPhase, apply_command
from engine.dice import Dice
from engine.player import Player
from engine.choices import UseGetOutOfJailFreeCardChoice

from demo.game import build_demo_game


def print_list(title: str, items: list[object]) -> None:
    print(f"{title}:")
    for item in items:
        print(f"  - {item}")
    if not items:
        print("  (none)")
        
def print_final_state(game: Game) -> None:
    print("\n" + "-" * 40 + "\nFinal state:")
    # Player state
    print("\nPlayer state:")
    for player in game.players:
        print(
            f"Player {player.id}: balance={player.balance} position={player.position} skip_turns={player.skip_turns}"
        )

    # Board state
    print("\nBoard state:")
    for tile in game.board.tiles:
        t = ""
        for attr, value in vars(tile).items():
            t += f"{attr}: {value}, "
        print(t)
        print("-" * 40)


def main() -> None:
    random.seed(1234)

    game = build_demo_game()

    game, events, choices = start_game(game)

    turns = 12
    for turn in range(1, turns + 1):
        player = game.current_player()
        print(
            f"\nTurn {turn} | Player {player.id} | balance={player.balance} pos={player.position} skip_turns={player.skip_turns}"
        )

        events = []

        while game.turn_phase != TurnPhase.END_TURN:
            if not choices:
                break  # No choices available, end turn

            # print_list("Available choices", choices)
            # Get the getoutofjailfree card choice if available, otherwise just take the first choice
            choice = next(
                (c for c in choices if isinstance(c, UseGetOutOfJailFreeCardChoice)),
                choices[0],
            )
            # print(f"Applying choice: {choice}")
            game, choice_events, choices = apply_command(game, choice)
            events.extend(choice_events)

        if game.turn_phase == TurnPhase.END_TURN:
            print("Ending turn...")
            game, end_events, choices = end_turn(game)
            events.extend(end_events)

        print_list("Events", events)

    print_final_state(game)


if __name__ == "__main__":
    main()
