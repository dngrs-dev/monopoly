from engine.auction import Auction
from engine.choices import AuctionBidChoice, AuctionPassChoice


def test_auction_start_sets_state_and_choices():
    auction = Auction(
        tile_position=3,
        base_price=100,
        initial_player_id=1,
        active_player_ids=[2, 3],
    )

    choices = auction.start()

    assert auction.step == 1
    assert auction.cursor_index == 0
    assert len(choices) == 2
    bid_choice = next(c for c in choices if isinstance(c, AuctionBidChoice))
    pass_choice = next(c for c in choices if isinstance(c, AuctionPassChoice))
    assert bid_choice.player_id == 2
    assert bid_choice.bid == 110
    assert pass_choice.player_id == 2


def test_auction_cursor_and_remove_bidder():
    auction = Auction(
        tile_position=1,
        base_price=200,
        initial_player_id=1,
        active_player_ids=[1, 2, 3],
        cursor_index=1,
    )

    auction.remove_bidder(1)

    assert auction.active_player_ids == [2, 3]
    assert auction.cursor_index == 0

    auction.advance_cursor()
    assert auction.active_player_id() == 3
