from dataclasses import dataclass, field
import random

from cards import Card


@dataclass
class Deck:
    cards: list[Card]
    draw_pile: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.discard_pile = self.cards.copy()

    def draw_card(self) -> Card:
        if not self.draw_pile:
            self.draw_pile = self.discard_pile.copy()
            self.discard_pile.clear()
            random.shuffle(self.draw_pile)
        card = self.draw_pile.pop()
        return card

    def discard_card(self, card: Card) -> None:
        self.discard_pile.append(card)
