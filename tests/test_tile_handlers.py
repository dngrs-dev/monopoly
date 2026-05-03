from engine.board import Board
from engine.cards import MoneyCard
from engine.deck import Deck
from engine.dice import Dice
from engine.events import PlayerDrewCard, PlayerPaidFine, PlayerPaidMoney
from engine.game import Game, TurnPhase
from engine.player import Player
from engine.tile_handlers import resolve_tile
from engine.tiles import ChanceTile, OwnableTile, PayTile, StartTile, Tile
from engine.choices import BuyPropertyChoice, DeclineBuyPropertyChoice


def test_ownable_tile_unowned_offers_buy_or_decline():
    board = Board(
        tiles=[
            StartTile(name="Go"),
            OwnableTile(name="A", price=100, rent=10),
        ]
    )
    game = Game(
        board=board,
        players=[Player(id=1, balance=200, position=1)],
        dice=Dice(),
    )

    game, _, choices = resolve_tile(board.get_tile(1), game)

    assert game.turn_phase == TurnPhase.AWAIT_CHOICE
    assert any(isinstance(c, BuyPropertyChoice) for c in choices)
    assert any(isinstance(c, DeclineBuyPropertyChoice) for c in choices)


def test_pay_tile_deducts_amount_and_emits_event():
    board = Board(tiles=[PayTile(name="Tax", amount=50)])
    game = Game(
        board=board,
        players=[Player(id=1, balance=100, position=0)],
        dice=Dice(),
    )

    game, events, _ = resolve_tile(board.get_tile(0), game)

    assert game.turn_phase == TurnPhase.END_TURN
    assert game.players[0].balance == 50
    assert any(isinstance(e, PlayerPaidFine) for e in events)


def test_chance_tile_draws_money_card_and_applies():
    deck = Deck(cards=[MoneyCard(amount=25)])
    board = Board(tiles=[ChanceTile(name="Chance", deck=deck), Tile(name="A")])
    game = Game(
        board=board,
        players=[Player(id=1, balance=0, position=0)],
        dice=Dice(),
    )

    game, events, _ = resolve_tile(board.get_tile(0), game)

    assert game.turn_phase == TurnPhase.END_TURN
    assert game.players[0].balance == 25
    assert any(isinstance(e, PlayerDrewCard) for e in events)
    assert any(isinstance(e, PlayerPaidMoney) for e in events)
