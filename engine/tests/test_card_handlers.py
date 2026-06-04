from engine.board import Board
from engine.cards import (
    CollectFromEachPlayerCard,
    GoToJailCard,
    MoneyCard,
    MoveStepsCard,
    PayEachPlayerCard,
    PayPerImprovementCard,
)
from engine.deck import Deck
from engine.dice import Dice
from engine.events import PlayerMoved, PlayerPaidMoney, PlayerWentToJail
from engine.game import Game, TurnPhase
from engine.player import Player
from engine.tiles import ChanceTile, JailTile, StreetTile, Tile
from engine.card_handlers import resolve_card


def build_game_with_chance(players, extra_tiles=None):
    deck = Deck(cards=[])
    tiles = [ChanceTile(name="Chance", deck=deck)]
    if extra_tiles:
        tiles.extend(extra_tiles)
    board = Board(tiles=tiles)
    return Game(board=board, players=players, dice=Dice())


def test_money_card_negative_creates_pending_payment():
    player = Player(id=1, balance=10, position=0)
    game = build_game_with_chance([player])

    game, events, _ = resolve_card(MoneyCard(amount=-50), game)

    assert game.turn_phase == TurnPhase.AWAIT_CHOICE
    assert game.pending_payment is not None
    assert game.pending_payment.amount == 50
    assert not any(isinstance(e, PlayerPaidMoney) for e in events)


def test_move_steps_card_moves_and_emits_event():
    player = Player(id=1, balance=0, position=0)
    game = build_game_with_chance([player], extra_tiles=[Tile(name="A"), Tile(name="B")])

    game, events, _ = resolve_card(MoveStepsCard(steps=2), game)

    assert player.position == 2
    assert any(isinstance(e, PlayerMoved) for e in events)
    assert game.turn_phase == TurnPhase.END_TURN


def test_go_to_jail_card_moves_player():
    player = Player(id=1, balance=0, position=0)
    game = build_game_with_chance(
        [player], extra_tiles=[Tile(name="A"), JailTile(name="Jail", skip_turns=2)]
    )

    game, events, _ = resolve_card(GoToJailCard(), game)

    assert player.position == 2
    assert player.in_jail is True
    assert player.skip_turns == 2
    assert any(isinstance(e, PlayerWentToJail) for e in events)


def test_pay_each_player_card_skips_bankrupt():
    payer = Player(id=1, balance=200, position=0)
    bankrupt = Player(id=2, balance=10, bankrupt=True, position=0)
    payee = Player(id=3, balance=0, position=0)
    game = build_game_with_chance([payer, bankrupt, payee])

    game, events, _ = resolve_card(PayEachPlayerCard(amount=50), game)

    assert payer.balance == 150
    assert bankrupt.balance == 10
    assert payee.balance == 50
    assert len(events) == 2


def test_collect_from_each_player_card_creates_pending_payment():
    collector = Player(id=1, balance=0, position=0)
    payer1 = Player(id=2, balance=10, position=0)
    payer2 = Player(id=3, balance=100, position=0)
    game = build_game_with_chance([collector, payer1, payer2])

    game, _, _ = resolve_card(CollectFromEachPlayerCard(amount=50), game)

    assert game.turn_phase == TurnPhase.AWAIT_CHOICE
    assert game.pending_payment is not None
    assert game.pending_payment.debtor_player_id == 2
    assert game.pending_payment.remaining_player_ids == [3]


def test_pay_per_improvement_card_total():
    player = Player(id=1, balance=500, position=0)
    street1 = StreetTile(
        name="S1",
        price=100,
        rent=10,
        group_id=1,
        improvement_prices=50,
        rent_schedule=[10, 20, 30],
        improvement_level=1,
        owner=1,
    )
    street2 = StreetTile(
        name="S2",
        price=120,
        rent=12,
        group_id=1,
        improvement_prices=50,
        rent_schedule=[12, 24, 36],
        improvement_level=2,
        owner=1,
    )
    game = build_game_with_chance([player], extra_tiles=[street1, street2])

    game, events, _ = resolve_card(PayPerImprovementCard(amount=[0, 50, 100]), game)

    assert player.balance == 350
    assert any(
        isinstance(e, PlayerPaidMoney) and e.amount == -150 for e in events
    )
