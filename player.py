from dataclasses import dataclass, field

from cards import Card


@dataclass
class Player:
    id: int
    balance: int
    position: int = 0
    skip_turns: int = 0
    bankrupt: bool = False
    in_jail: bool = False
    cards: list[Card] = field(default_factory=list)

    def move(self, steps: int, board_size: int):
        self.position = (self.position + steps) % board_size

    def update_balance(self, amount: int):
        self.balance += amount
