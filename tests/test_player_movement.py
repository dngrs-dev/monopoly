from engine.board import Board
from engine.events import PlayerLandedOnStart, PlayerPassedStart
from engine.player import Player
from engine.tiles import StartTile, Tile


def test_player_lands_on_start_gets_pass_and_land_bonus():
    board = Board(
        tiles=[
            StartTile(name="Go", pass_bonus=200, land_bonus=100),
            Tile(name="X"),
            Tile(name="Y"),
            Tile(name="Z"),
        ]
    )
    player = Player(id=1, balance=0, position=3)

    events = player.move_steps(1, board)

    assert player.position == 0
    assert player.balance == 300
    assert [type(e) for e in events] == [PlayerPassedStart, PlayerLandedOnStart]


def test_player_wraps_past_start_gets_pass_bonus_only():
    board = Board(
        tiles=[
            StartTile(name="Go", pass_bonus=200, land_bonus=100),
            Tile(name="X"),
            Tile(name="Y"),
            Tile(name="Z"),
        ]
    )
    player = Player(id=1, balance=10, position=3)

    events = player.move_steps(2, board)

    assert player.position == 1
    assert player.balance == 210
    assert len(events) == 1
    assert isinstance(events[0], PlayerPassedStart)


def test_player_multiple_laps_awards_pass_bonus_each_lap():
    board = Board(
        tiles=[
            StartTile(name="Go", pass_bonus=200, land_bonus=100),
            Tile(name="X"),
            Tile(name="Y"),
            Tile(name="Z"),
        ]
    )
    player = Player(id=1, balance=0, position=1)

    events = player.move_steps(9, board)

    assert player.position == 2
    assert player.balance == 400
    assert sum(isinstance(e, PlayerPassedStart) for e in events) == 2


def test_player_can_have_multiple_start_tiles():
    board = Board(
        tiles=[
            StartTile(name="Go", pass_bonus=200, land_bonus=100),
            Tile(name="X"),
            StartTile(name="AltStart", pass_bonus=50, land_bonus=25),
            Tile(name="Z"),
        ]
    )
    player = Player(id=1, balance=0, position=1)

    events = player.move_steps(1, board)

    assert player.position == 2
    assert player.balance == 75
    assert [type(e) for e in events] == [PlayerPassedStart, PlayerLandedOnStart]
    assert events[0].amount == 50
    assert events[1].amount == 25
