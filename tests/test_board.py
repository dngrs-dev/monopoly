from engine.board import Board
from engine.tiles import StartTile, Tile


def test_board_finds_start_tiles_on_init():
    tiles = [
        StartTile(name="Go"),
        Tile(name="A"),
        StartTile(name="Start2"),
        Tile(name="B"),
    ]
    board = Board(tiles=tiles)

    assert board.size() == 4
    assert board.start_tiles == [0, 2]
    assert board.get_tile(2).name == "Start2"
