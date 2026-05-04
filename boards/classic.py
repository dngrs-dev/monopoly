from engine.board import Board
from engine.cards import (
    MoneyCard,
    GetOutOfJailFreeCard,
    MoveToPositionCard,
    MoveToNearestTileByTypeCard,
    MoveStepsCard,
    PayEachPlayerCard,
    PayPerImprovementCard,
    CollectFromEachPlayerCard,
    GoToJailCard,
)
from engine.deck import Deck
from engine.tiles import (
    StartTile,
    StreetTile,
    ChanceTile,
    PayTile,
    RailroadTile,
    JailTile,
    UtilityTile,
    NoneTile,
    GoToJailTile,
)


def build_chance_deck() -> Deck:
    return Deck(
        cards=[
            MoveToNearestTileByTypeCard(tile_type=StartTile),
            GoToJailCard(),
            MoveToPositionCard(position=3),  # Illinois Avenue
            MoveToPositionCard(position=12),  # St. Charles Place
            MoveToNearestTileByTypeCard(tile_type=UtilityTile),
            MoveToNearestTileByTypeCard(tile_type=RailroadTile),
            MoveToNearestTileByTypeCard(tile_type=RailroadTile),
            MoneyCard(amount=50),
            GetOutOfJailFreeCard(),
            MoveStepsCard(steps=-3),
            PayPerImprovementCard(amount=[25, 25, 25, 25, 100]),
            MoneyCard(amount=-15),
            MoveToPositionCard(position=5),  # Reading Railroad
            MoveToPositionCard(position=39),  # Boardwalk
            PayEachPlayerCard(amount=50),
            MoneyCard(amount=150),
        ]
    )


def build_community_chest_deck() -> Deck:
    return Deck(
        cards=[
            MoveToNearestTileByTypeCard(tile_type=StartTile),
            MoneyCard(amount=200),
            MoneyCard(amount=-50),
            MoneyCard(amount=50),
            GetOutOfJailFreeCard(),
            GoToJailCard(),
            CollectFromEachPlayerCard(amount=50),
            MoneyCard(amount=100),
            MoneyCard(amount=20),
            CollectFromEachPlayerCard(amount=10),
            MoneyCard(amount=100),
            MoneyCard(amount=-100),
            MoneyCard(amount=-150),
            MoneyCard(amount=25),
            PayPerImprovementCard(amount=[40, 40, 40, 40, 115]),
            MoneyCard(amount=10),
        ]
    )


def build_classic_board() -> Board:
    community_deck = build_community_chest_deck()
    chance_deck = build_chance_deck()
    return Board(
        tiles=[
            StartTile(name="go", pass_bonus=200, land_bonus=100),
            StreetTile(
                name="mediterranean_avenue",
                group_id=0,
                price=60,
                rent_schedule=[2, 10, 30, 90, 160, 250],
                improvement_prices=[50, 50, 50, 50, 150],
            ),
            ChanceTile(name="community_chest_1", deck=community_deck),
            StreetTile(
                name="baltic_avenue",
                group_id=0,
                price=60,
                rent_schedule=[4, 20, 60, 180, 320, 450],
                improvement_prices=[50, 50, 50, 50, 150],
            ),
            PayTile(name="income_tax", amount=200),
            RailroadTile(
                name="reading_railroad",
                group_id=1,
                price=200,
                rent_schedule=[25, 50, 100, 200],
            ),
            StreetTile(
                name="oriental_avenue",
                group_id=2,
                price=100,
                rent_schedule=[6, 30, 90, 270, 400, 550],
                improvement_prices=[50, 50, 50, 50, 150],
            ),
            ChanceTile(name="chance_1", deck=chance_deck),
            StreetTile(
                name="vermont_avenue",
                group_id=2,
                price=100,
                rent_schedule=[6, 30, 90, 270, 400, 550],
                improvement_prices=[50, 50, 50, 50, 150],
            ),
            StreetTile(
                name="connecticut_avenue",
                group_id=2,
                price=120,
                rent_schedule=[8, 40, 100, 300, 450, 600],
                improvement_prices=[50, 50, 50, 50, 150],
            ),
            JailTile(name="jail"),
            StreetTile(
                name="st_charles_place",
                group_id=3,
                price=140,
                rent_schedule=[10, 50, 150, 450, 625, 750],
                improvement_prices=[100, 100, 100, 100, 200],
            ),
            UtilityTile(
                name="electric_company", group_id=4, price=150, rent_multiplier=[4, 10]
            ),
            StreetTile(
                name="states_avenue",
                group_id=3,
                price=140,
                rent_schedule=[10, 50, 150, 450, 625, 750],
                improvement_prices=[100, 100, 100, 100, 200],
            ),
            StreetTile(
                name="virginia_avenue",
                group_id=3,
                price=160,
                rent_schedule=[12, 60, 180, 500, 700, 900],
                improvement_prices=[100, 100, 100, 100, 200],
            ),
            RailroadTile(
                name="pennsylvania_railroad",
                group_id=1,
                price=200,
                rent_schedule=[25, 50, 100, 200],
            ),
            StreetTile(
                name="st_james_place",
                group_id=4,
                price=180,
                rent_schedule=[14, 70, 200, 550, 750, 950],
                improvement_prices=[100, 100, 100, 100, 200],
            ),
            ChanceTile(name="chance_2", deck=chance_deck),
            StreetTile(
                name="tennessee_avenue",
                group_id=4,
                price=180,
                rent_schedule=[14, 70, 200, 550, 750, 950],
                improvement_prices=[100, 100, 100, 100, 200],
            ),
            StreetTile(
                name="new_york_avenue",
                group_id=4,
                price=200,
                rent_schedule=[16, 80, 220, 600, 800, 1000],
                improvement_prices=[100, 100, 100, 100, 200],
            ),
            NoneTile(name="free_parking"),
            StreetTile(
                name="kentucky_avenue",
                group_id=5,
                price=220,
                rent_schedule=[18, 90, 250, 700, 875, 1050],
                improvement_prices=[150, 150, 150, 150, 250],
            ),
            ChanceTile(name="community_chest_2", deck=community_deck),
            StreetTile(
                name="indiana_avenue",
                group_id=5,
                price=220,
                rent_schedule=[18, 90, 250, 700, 875, 1050],
                improvement_prices=[150, 150, 150, 150, 250],
            ),
            StreetTile(
                name="illinois_avenue",
                group_id=5,
                price=240,
                rent_schedule=[20, 100, 300, 750, 925, 1100],
                improvement_prices=[150, 150, 150, 150, 250],
            ),
            RailroadTile(
                name="b_and_o_railroad",
                group_id=1,
                price=200,
                rent_schedule=[25, 50, 100, 200],
            ),
            StreetTile(
                name="atlantic_avenue",
                group_id=6,
                price=260,
                rent_schedule=[22, 110, 330, 800, 975, 1150],
                improvement_prices=[150, 150, 150, 150, 250],
            ),
            StreetTile(
                name="ventnor_avenue",
                group_id=6,
                price=260,
                rent_schedule=[22, 110, 330, 800, 975, 1150],
                improvement_prices=[150, 150, 150, 150, 250],
            ),
            UtilityTile(
                name="water_works", group_id=4, price=150, rent_multiplier=[4, 10]
            ),
            StreetTile(
                name="marvin_gardens",
                group_id=6,
                price=280,
                rent_schedule=[24, 120, 360, 850, 1025, 1200],
                improvement_prices=[150, 150, 150, 150, 250],
            ),
            GoToJailTile(name="go_to_jail"),
            StreetTile(
                name="pacific_avenue",
                group_id=7,
                price=300,
                rent_schedule=[26, 130, 390, 900, 1100, 1275],
                improvement_prices=[200, 200, 200, 200, 300],
            ),
            StreetTile(
                name="north_carolina_avenue",
                group_id=7,
                price=300,
                rent_schedule=[26, 130, 390, 900, 1100, 1275],
                improvement_prices=[200, 200, 200, 200, 300],
            ),
            ChanceTile(name="community_chest_3", deck=community_deck),
            StreetTile(
                name="pennsylvania_avenue",
                group_id=7,
                price=320,
                rent_schedule=[28, 150, 450, 1000, 1200, 1400],
                improvement_prices=[200, 200, 200, 200, 300],
            ),
            RailroadTile(
                name="short_line",
                group_id=1,
                price=200,
                rent_schedule=[25, 50, 100, 200],
            ),
            ChanceTile(name="chance_3", deck=chance_deck),
            StreetTile(
                name="park_place",
                group_id=8,
                price=350,
                rent_schedule=[35, 175, 500, 1100, 1300, 1500],
                improvement_prices=[200, 200, 200, 200, 300],
            ),
            PayTile(name="luxury_tax", amount=100),
            StreetTile(
                name="boardwalk",
                group_id=8,
                price=400,
                rent_schedule=[50, 200, 600, 1400, 1700, 2000],
                improvement_prices=[200, 200, 200, 200, 300],
            ),
        ]
    )


if __name__ == "__main__":
    board = build_classic_board()
    print(board)
