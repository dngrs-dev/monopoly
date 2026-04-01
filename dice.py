from dataclasses import dataclass
import random

@dataclass
class Dice:
    min_value: int = 1
    max_value: int = 6
    last_roll: int = -1
    
    def roll(self) -> int:
        r = random.randint(self.min_value, self.max_value)
        self.last_roll = r
        return r