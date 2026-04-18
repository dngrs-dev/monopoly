from engine.game import Game
from engine.player import Player
from engine.dice import Dice

from demo.board import build_demo_board


def build_demo_game() -> Game:
    board = build_demo_board()
    game = Game(
        board=board,
        players=[Player(id=1, balance=500), Player(id=2, balance=500)],
        dice=Dice(),
    )
    return game
