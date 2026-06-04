from engine.tiles import OwnableTile, StreetTile


def test_ownable_tile_mortgage_helpers():
    tile = OwnableTile(name="A", price=200, rent=10)

    assert tile.mortgage_value() == 100
    assert tile.unmortgage_value() == 110


def test_street_tile_improvement_price_helpers():
    tile = StreetTile(
        name="A",
        price=100,
        rent=10,
        group_id=1,
        improvement_prices=[50, 100, 150],
        rent_schedule=[10, 20, 30, 40],
        improvement_level=1,
    )

    assert tile.improvement_buy_price() == 100
    assert tile.improvement_sell_price() == 25


def test_street_tile_improvement_price_helpers_with_scalar_prices():
    tile = StreetTile(
        name="B",
        price=100,
        rent=10,
        group_id=1,
        improvement_prices=60,
        rent_schedule=[10, 20, 30],
        improvement_level=1,
    )

    assert tile.improvement_buy_price() == 60
    assert tile.improvement_sell_price() == 30
