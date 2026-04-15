from __future__ import annotations

from engine.board import Board
from engine.deck import Deck
from engine.cards import (
    MoveStepsCard,
    MoveToPositionCard,
    MoneyCard,
    GoToJailCard,
    GetOutOfJailFreeCard,
)
from engine.tiles import (
    Tile,
    StartTile,
    ChanceTile,
    JailTile,
    GoToJailTile,
    StreetTile,
    RailroadTile,
    UtilityTile,
)


# Classic Monopoly board positions (0-indexed)
GO = 0
READING_RAILROAD = 5
JAIL = 10
ST_CHARLES_PLACE = 11
ILLINOIS_AVENUE = 24
GO_TO_JAIL = 30
BOARDWALK = 39


def build_classic_chance_deck() -> Deck:
    # Keep cards limited to what the engine currently supports.
    return Deck(
        cards=[
            MoveToPositionCard(position=GO),
            MoveToPositionCard(position=ILLINOIS_AVENUE),
            MoveToPositionCard(position=ST_CHARLES_PLACE),
            MoveToPositionCard(position=READING_RAILROAD),
            MoneyCard(amount=50),
            MoneyCard(amount=-15),
            MoveStepsCard(steps=3),
            GoToJailCard(),
            GetOutOfJailFreeCard(),
        ]
    )


def build_classic_community_chest_deck() -> Deck:
    return Deck(
        cards=[
            MoveToPositionCard(position=GO),
            MoneyCard(amount=200),
            MoneyCard(amount=50),
            MoneyCard(amount=-50),
            GetOutOfJailFreeCard(),
        ]
    )


def _street(
    *,
    name: str,
    group_id: int,
    price: int,
    base_rent: int,
    house_cost: int,
) -> StreetTile:
    # Only base rent is currently used by the demo/engine.
    # Extra levels are included so the tile is future-proof if improvements are enabled.
    rent_schedule = [
        base_rent,
        base_rent * 5,
        base_rent * 15,
        base_rent * 35,
        base_rent * 45,
        base_rent * 50,
    ]
    return StreetTile(
        name=name,
        price=price,
        rent=rent_schedule[0],
        group_id=group_id,
        improvement_prices=house_cost,
        rent_schedule=rent_schedule,
    )


def _railroad(*, name: str) -> RailroadTile:
    return RailroadTile(
        name=name,
        price=200,
        rent=25,
        group_id=9,
        rent_schedule=[25, 50, 100, 200],
    )


def _utility(*, name: str) -> UtilityTile:
    # The engine currently computes utility rent as: rent_multiplier * utilities_owned.
    return UtilityTile(
        name=name,
        price=150,
        rent=25,
        group_id=10,
        rent_multiplier=25,
    )


def build_demo_board() -> Board:
    chance_deck = build_classic_chance_deck()
    chest_deck = build_classic_community_chest_deck()

    tiles = [
        StartTile(name="Go", pass_bonus=200, land_bonus=0),
        _street(
            name="Mediterranean Avenue",
            group_id=1,
            price=60,
            base_rent=2,
            house_cost=50,
        ),
        ChanceTile(name="Community Chest", deck=chest_deck),
        _street(name="Baltic Avenue", group_id=1, price=60, base_rent=4, house_cost=50),
        Tile(name="Income Tax"),
        _railroad(name="Reading Railroad"),
        _street(
            name="Oriental Avenue",
            group_id=2,
            price=100,
            base_rent=6,
            house_cost=50,
        ),
        ChanceTile(name="Chance", deck=chance_deck),
        _street(name="Vermont Avenue", group_id=2, price=100, base_rent=6, house_cost=50),
        _street(
            name="Connecticut Avenue",
            group_id=2,
            price=120,
            base_rent=8,
            house_cost=50,
        ),
        JailTile(name="Jail / Just Visiting"),
        _street(
            name="St. Charles Place",
            group_id=3,
            price=140,
            base_rent=10,
            house_cost=100,
        ),
        _utility(name="Electric Company"),
        _street(name="States Avenue", group_id=3, price=140, base_rent=10, house_cost=100),
        _street(
            name="Virginia Avenue",
            group_id=3,
            price=160,
            base_rent=12,
            house_cost=100,
        ),
        _railroad(name="Pennsylvania Railroad"),
        _street(
            name="St. James Place",
            group_id=4,
            price=180,
            base_rent=14,
            house_cost=100,
        ),
        ChanceTile(name="Community Chest", deck=chest_deck),
        _street(name="Tennessee Avenue", group_id=4, price=180, base_rent=14, house_cost=100),
        _street(
            name="New York Avenue",
            group_id=4,
            price=200,
            base_rent=16,
            house_cost=100,
        ),
        Tile(name="Free Parking"),
        _street(
            name="Kentucky Avenue",
            group_id=5,
            price=220,
            base_rent=18,
            house_cost=150,
        ),
        ChanceTile(name="Chance", deck=chance_deck),
        _street(name="Indiana Avenue", group_id=5, price=220, base_rent=18, house_cost=150),
        _street(
            name="Illinois Avenue",
            group_id=5,
            price=240,
            base_rent=20,
            house_cost=150,
        ),
        _railroad(name="B. & O. Railroad"),
        _street(
            name="Atlantic Avenue",
            group_id=6,
            price=260,
            base_rent=22,
            house_cost=150,
        ),
        _street(name="Ventnor Avenue", group_id=6, price=260, base_rent=22, house_cost=150),
        _utility(name="Water Works"),
        _street(
            name="Marvin Gardens",
            group_id=6,
            price=280,
            base_rent=24,
            house_cost=150,
        ),
        GoToJailTile(name="Go To Jail"),
        _street(
            name="Pacific Avenue",
            group_id=7,
            price=300,
            base_rent=26,
            house_cost=200,
        ),
        _street(
            name="North Carolina Avenue",
            group_id=7,
            price=300,
            base_rent=26,
            house_cost=200,
        ),
        ChanceTile(name="Community Chest", deck=chest_deck),
        _street(
            name="Pennsylvania Avenue",
            group_id=7,
            price=320,
            base_rent=28,
            house_cost=200,
        ),
        _railroad(name="Short Line"),
        ChanceTile(name="Chance", deck=chance_deck),
        _street(
            name="Park Place",
            group_id=8,
            price=350,
            base_rent=35,
            house_cost=200,
        ),
        Tile(name="Luxury Tax"),
        _street(
            name="Boardwalk",
            group_id=8,
            price=400,
            base_rent=50,
            house_cost=200,
        ),
    ]

    if len(tiles) != 40:
        raise ValueError(f"Classic board must have 40 tiles; got {len(tiles)}")

    return Board(tiles=tiles)

if __name__ == "__main__":
    board = build_demo_board()
    for i, tile in enumerate(board.tiles):
        print(f"{i}: {tile.name} ({type(tile).__name__})")