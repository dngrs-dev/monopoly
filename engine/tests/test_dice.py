import random

from engine.dice import Dice


def test_dice_roll_sets_last_values(monkeypatch):
    rolls = iter([2, 5])

    def fake_randint(a: int, b: int) -> int:
        return next(rolls)

    monkeypatch.setattr(random, "randint", fake_randint)

    dice = Dice()
    d1, d2 = dice.roll()

    assert (d1, d2) == (2, 5)
    assert dice.last_roll_pair == (2, 5)
    assert dice.last_roll == 7
