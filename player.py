from dataclasses import dataclass

from cards import Card


@dataclass
class Player:
    id: int
    balance: int
    position: int = 0
    skip_turns: int = 0
    bankrupt: bool = False
    in_jail: bool = False
    cards: list[Card] = None

    def move(self, steps: int, board_size: int):
        self.position = (self.position + steps) % board_size

    def update_balance(self, amount: int):
        self.balance += amount
