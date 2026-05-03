from engine.board import Board
from engine.dice import Dice
from engine.events import MoveReason, PlayerMoved, PlayerWentToJail
from engine.game import Game, TurnPhase
from engine.player import Player
from engine.tiles import JailTile, Tile


def test_game_active_player_ids_excludes_bankrupt():
    board = Board(tiles=[Tile(name="A")])
    game = Game(
        board=board,
        players=[
            Player(id=1, balance=100),
            Player(id=2, balance=50, bankrupt=True),
            Player(id=3, balance=75),
        ],
        dice=Dice(),
    )

    assert game.active_player_ids() == [1, 3]
    assert game.active_player_ids(exclude_ids={1}) == [3]


def test_game_send_player_to_jail_sets_state_and_events():
    board = Board(tiles=[Tile(name="A"), JailTile(name="Jail", skip_turns=2)])
    player = Player(id=1, balance=100, position=0)
    game = Game(board=board, players=[player], dice=Dice())

    events = game.send_player_to_jail(player, reason=MoveReason.TILE_EFFECT)

    assert player.position == 1
    assert player.in_jail is True
    assert player.skip_turns == 2
    assert any(isinstance(e, PlayerMoved) for e in events)
    assert any(isinstance(e, PlayerWentToJail) for e in events)


def test_game_pay_each_player_skips_bankrupt():
    board = Board(tiles=[Tile(name="A")])
    payer = Player(id=1, balance=200)
    bankrupt = Player(id=2, balance=10, bankrupt=True)
    payee = Player(id=3, balance=0)
    game = Game(board=board, players=[payer, bankrupt, payee], dice=Dice())

    events = game.pay_each_player(payer_id=1, amount=50)

    assert payer.balance == 150
    assert bankrupt.balance == 10
    assert payee.balance == 50
    assert len(events) == 2


def test_game_collect_from_each_player_creates_pending_payment():
    board = Board(tiles=[Tile(name="A")])
    payee = Player(id=1, balance=0)
    payer1 = Player(id=2, balance=10)
    payer2 = Player(id=3, balance=100)
    game = Game(board=board, players=[payee, payer1, payer2], dice=Dice())

    game, events, _ = game.collect_from_each_player(
        payee_id=1,
        payer_ids=[2, 3],
        amount=50,
        end_turn=True,
    )

    assert events == []
    assert game.turn_phase == TurnPhase.AWAIT_CHOICE
    assert game.pending_payment is not None
    assert game.pending_payment.debtor_player_id == 2
    assert game.pending_payment.remaining_player_ids == [3]
