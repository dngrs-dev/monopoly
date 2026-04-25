from engine.board import Board
from engine.dice import Dice
from engine.game import Game, TurnPhase, apply_command
from engine.player import Player
from engine.tile_handlers import resolve_tile
from engine.tiles import OwnableTile, StartTile
from engine.choices import (
    DeclareBankruptcyChoice,
    MortgagePropertyChoice,
    PayPendingPaymentChoice,
)
from engine.events import PlayerPaidRent


def test_insufficient_rent_creates_pending_payment_and_offers_mortgage_or_bankruptcy():
    board = Board(
        tiles=[
            StartTile(name="Go"),
            OwnableTile(name="A", price=100, rent=50, owner=2),
            OwnableTile(name="B", price=60, rent=10, owner=1),
        ]
    )
    game = Game(
        board=board,
        players=[
            Player(id=1, balance=10, position=1),
            Player(id=2, balance=500, position=0),
        ],
        dice=Dice(),
    )

    game, events, choices = resolve_tile(board.get_tile(1), game)

    assert game.turn_phase == TurnPhase.AWAIT_CHOICE
    assert game.pending_payment is not None
    assert game.pending_payment.amount == 50
    assert game.pending_payment.creditor_player_id == 2

    assert any(isinstance(c, DeclareBankruptcyChoice) for c in choices)
    assert any(
        isinstance(c, MortgagePropertyChoice) and c.property_position == 2
        for c in choices
    )
    assert not any(isinstance(c, PayPendingPaymentChoice) for c in choices)


def test_mortgage_then_pay_pending_rent_transfers_money_and_clears_pending_payment():
    board = Board(
        tiles=[
            StartTile(name="Go"),
            OwnableTile(name="A", price=100, rent=50, owner=2),
            OwnableTile(name="B", price=100, rent=10, owner=1),
        ]
    )
    game = Game(
        board=board,
        players=[
            Player(id=1, balance=10, position=1),
            Player(id=2, balance=500, position=0),
        ],
        dice=Dice(),
    )

    game, _, choices = resolve_tile(board.get_tile(1), game)
    mortgage = next(c for c in choices if isinstance(c, MortgagePropertyChoice))

    game, _, choices = apply_command(game, mortgage)

    pay = next(c for c in choices if isinstance(c, PayPendingPaymentChoice))
    game, pay_events, _ = apply_command(game, pay)

    assert game.turn_phase == TurnPhase.END_TURN
    assert game.pending_payment is None
    assert game.players[0].balance == 10
    assert game.players[1].balance == 550

    assert any(
        isinstance(e, PlayerPaidRent)
        and e.player_id == 1
        and e.to_player_id == 2
        and e.property_name == "A"
        and e.rent == 50
        for e in pay_events
    )
