from engine.game import Game
from engine.player import Player
from engine.dice import Dice

from boards.classic import build_classic_board


def build_demo_game() -> Game:
    board = build_classic_board()
    game = Game(
        board=board,
        players=[Player(id=1, balance=500), Player(id=2, balance=500)],
        dice=Dice(),
    )
    return game

if __name__ == "__main__":
    game = build_demo_game()
    print(game)