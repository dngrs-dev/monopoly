from dataclasses import dataclass, field

from engine.choices import Choice, AuctionBidChoice, AuctionPassChoice


@dataclass
class Auction:
    tile_position: int
    base_price: int
    initial_player_id: int

    step: int = 0
    cursor_index: int = 0
    last_bidder_id: int | None = None
    last_bid_amount: int | None = None
    active_player_ids: list[int] = field(default_factory=list)

    def active_bid(self) -> int:
        # Keep bids integer-valued to match balances.
        return int(self.base_price * (1 + 0.1 * self.step))

    def start(self) -> list[Choice]:
        # Start the auction with the initial player
        self.step = 1
        self.cursor_index = 0
        return self.current_choices()

    def check_auction_end(self) -> bool:
        # Auction ends when zero or one active player remains.
        # 1: winner
        # 0: nobody bid / everybody passed
        return len(self.active_player_ids) <= 1
    
    def active_player_id(self) -> int:
        return self.active_player_ids[self.cursor_index]

    def current_choices(self) -> list[Choice]:
        player_id = self.active_player_id()
        return [
            AuctionBidChoice(
                player_id=player_id,
                tile_position=self.tile_position,
                bid=self.active_bid(),
            ),
            AuctionPassChoice(
                player_id=player_id,
                tile_position=self.tile_position,
            ),
        ]

    def advance_cursor(self) -> None:
        self.cursor_index = (self.cursor_index + 1) % len(self.active_player_ids)

    def remove_bidder(self, player_id: int) -> None:
        removed_index = self.active_player_ids.index(player_id)
        self.active_player_ids.pop(removed_index)
        if removed_index < self.cursor_index:
            self.cursor_index -= 1
        if self.active_player_ids and self.cursor_index >= len(self.active_player_ids):
            self.cursor_index = 0
    