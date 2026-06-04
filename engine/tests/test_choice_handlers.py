from engine.auction import Auction
from engine.board import Board
from engine.cards import GetOutOfJailFreeCard
from engine.choices import (
    AuctionBidChoice,
    AuctionPassChoice,
    DeclineBuyPropertyChoice,
    RollDiceChoice,
    TryDoublesJailChoice,
    UseGetOutOfJailFreeCardChoice,
)
from engine.deck import Deck
from engine.dice import Dice
from engine.events import PlayerMoved, PlayerReleasedFromJail, PlayerRolledDice
from engine.game import Game, TurnPhase, apply_command
from engine.player import Player
from engine.rules import Rules
from engine.tiles import JailTile, OwnableTile, Tile
from engine.events import AuctionStarted


def fixed_roll(dice: Dice, d1: int, d2: int) -> None:
    def _roll() -> tuple[int, int]:
        dice.last_roll_pair = (d1, d2)
        dice.last_roll = d1 + d2
        return d1, d2

    dice.roll = _roll


def test_roll_dice_choice_moves_and_ends_turn():
    board = Board(tiles=[Tile(name="A"), Tile(name="B"), Tile(name="C"), Tile(name="D")])
    game = Game(
        board=board,
        players=[Player(id=1, balance=0, position=0)],
        dice=Dice(),
    )
    fixed_roll(game.dice, 2, 3)

    game, events, _ = apply_command(game, RollDiceChoice(player_id=1))

    assert game.turn_phase == TurnPhase.END_TURN
    assert game.current_player().position == 1
    assert any(isinstance(e, PlayerRolledDice) for e in events)
    assert any(isinstance(e, PlayerMoved) for e in events)


def test_try_doubles_jail_choice_releases_and_moves():
    board = Board(tiles=[Tile(name="A"), Tile(name="B"), Tile(name="C")])
    player = Player(id=1, balance=0, position=0, in_jail=True, skip_turns=1)
    game = Game(board=board, players=[player], dice=Dice())
    fixed_roll(game.dice, 3, 3)

    game, events, _ = apply_command(game, TryDoublesJailChoice(player_id=1))

    assert player.in_jail is False
    assert player.skip_turns == 0
    assert any(isinstance(e, PlayerReleasedFromJail) for e in events)
    assert any(isinstance(e, PlayerMoved) for e in events)


def test_use_get_out_of_jail_free_card_choice_returns_card():
    deck = Deck(cards=[])
    card = GetOutOfJailFreeCard(origin_deck=deck)
    player = Player(id=1, balance=0, position=0, in_jail=True)
    player.cards.append(card)
    game = Game(board=Board(tiles=[JailTile(name="Jail")]), players=[player], dice=Dice())

    game, _, choices = apply_command(game, UseGetOutOfJailFreeCardChoice(player_id=1))

    assert player.in_jail is False
    assert player.cards == []
    assert deck.discard_pile[-1] == card
    assert any(isinstance(c, RollDiceChoice) for c in choices)


def test_decline_buy_property_starts_auction():
    board = Board(tiles=[Tile(name="Start"), OwnableTile(name="A", price=100, rent=10)])
    game = Game(
        board=board,
        players=[
            Player(id=1, balance=200, position=1),
            Player(id=2, balance=200, position=0),
        ],
        dice=Dice(),
        rules=Rules(auction_enabled=True),
    )

    game, events, choices = apply_command(
        game, DeclineBuyPropertyChoice(player_id=1)
    )

    assert game.auction is not None
    assert any(isinstance(e, AuctionStarted) for e in events)
    assert any(isinstance(c, AuctionBidChoice) for c in choices)
    assert any(isinstance(c, AuctionPassChoice) for c in choices)


def test_auction_awards_last_bidder_on_pass():
    tile = OwnableTile(name="A", price=100, rent=10)
    board = Board(tiles=[Tile(name="Start"), tile])
    player1 = Player(id=1, balance=500, position=0)
    player2 = Player(id=2, balance=500, position=0)
    game = Game(board=board, players=[player1, player2], dice=Dice())
    game.turn_phase = TurnPhase.AWAIT_CHOICE

    auction = Auction(
        tile_position=1,
        base_price=100,
        initial_player_id=1,
        step=1,
        cursor_index=0,
        active_player_ids=[1, 2],
    )
    game.auction = auction

    bid = AuctionBidChoice(
        player_id=1, tile_position=1, bid=auction.active_bid()
    )
    game, _, choices = apply_command(game, bid)

    pass_choice = AuctionPassChoice(player_id=2, tile_position=1)
    game, _, _ = apply_command(game, pass_choice)

    assert game.auction is None
    assert tile.owner == 1
    assert player1.balance == 390
    assert game.turn_phase == TurnPhase.END_TURN
