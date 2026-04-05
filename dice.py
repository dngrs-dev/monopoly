from dataclasses import dataclass
import random


@dataclass
class Dice:
    min_value: int = 1
    max_value: int = 6
    last_roll: int = None
    last_roll_pair: tuple[int, int] = None

    def roll(self) -> tuple[int, int]:
        d1 = random.randint(self.min_value, self.max_value)
        d2 = random.randint(self.min_value, self.max_value)
        self.last_roll_pair = (d1, d2)
        self.last_roll = d1 + d2
        return d1, d2
