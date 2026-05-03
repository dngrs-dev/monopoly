from dataclasses import dataclass
from engine.deck import Deck


@dataclass
class Tile:
    name: str


@dataclass(kw_only=True)
class OwnableTile(Tile):  # Base class, rent calculated in tile handler
    price: int
    rent: int
    owner: int | None = None
    mortgaged: bool = False

    def mortgage_value(self) -> int:
        return self.price // 2

    def unmortgage_value(self) -> int:
        return int(self.price * 0.55)


@dataclass
class StreetTile(OwnableTile):
    group_id: int
    improvement_prices: (
        list[int] | int
    )  # must be the same length as rent_schedule or a single int if all improvements have the same price
    rent_schedule: list[
        int
    ]  # index 0 = no houses, other -> number of improvement level
    improvement_level: int = 0
    improvement_sell_price_multiplier: float = 0.5

    def improvement_buy_price(self) -> int:
        if isinstance(self.improvement_prices, int):
            return self.improvement_prices
        return self.improvement_prices[self.improvement_level]

    def improvement_sell_price(self) -> int:
        if isinstance(self.improvement_prices, int):
            last_improvement_price = self.improvement_prices
        else:
            last_improvement_price = self.improvement_prices[self.improvement_level - 1]
        return int(last_improvement_price * self.improvement_sell_price_multiplier)


@dataclass
class RailroadTile(OwnableTile):
    group_id: int
    rent_schedule: list[
        int
    ]  # index 0 - basic rent, other -> number of railroads owned by same player


@dataclass
class UtilityTile(OwnableTile):
    group_id: int
    rent_multiplier: list[int] # index 0 - basic multiplier, other -> number of utilities owned by same player


@dataclass
class StartTile(Tile):
    pass_bonus: int = 200
    land_bonus: int = 100


@dataclass
class JailTile(Tile):
    skip_turns: int = 3
    fine: int = 50


@dataclass
class ChanceTile(Tile):
    deck: Deck


@dataclass
class GoToJailTile(Tile):
    pass


@dataclass
class NoneTile(Tile):
    pass # Free parking or similar, no action when landed on


@dataclass
class PayTile(Tile):
    amount: int
