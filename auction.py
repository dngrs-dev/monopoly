from dataclasses import dataclass, field

from choices import Choice, AuctionBidChoice, AuctionPassChoice


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
        return self.base_price * (1 + 0.1 * self.step)

    def start(self) -> list[Choice]:
        # Start the auction with the initial player
        choices: list[Choice] = []
        self.step = 1
        self.cursor_index = 0
        choices.append(
            AuctionBidChoice(
                player_id=self.active_player_ids[self.cursor_index],
                tile_position=self.tile_position,
                bid=self.active_bid(),
            )
        )
        choices.append(
            AuctionPassChoice(
                player_id=self.active_player_ids[self.cursor_index],
                tile_position=self.tile_position,
            )
        )
        return choices

    def check_auction_end(self) -> bool:
        # Auction ends when only one active player remains
        return len(self.active_player_ids) == 1
    
    def active_player_id(self) -> int:
        return self.active_player_ids[self.cursor_index]
    