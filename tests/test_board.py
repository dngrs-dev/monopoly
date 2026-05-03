from engine.board import Board
from engine.tiles import JailTile, StartTile, Tile


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


def test_board_find_tile_position():
    tiles = [
        Tile(name="A"),
        JailTile(name="Jail"),
        Tile(name="B"),
    ]
    board = Board(tiles=tiles)

    assert board.find_tile_position(JailTile) == 1
