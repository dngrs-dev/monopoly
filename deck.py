from dataclasses import dataclass, field

from cards import Card


@dataclass
class Deck:
    cards: list[Card]
    draw_pile: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)

    def draw_card(self) -> Card:
        if not self.draw_pile:
            self.draw_pile = self.cards.copy()
            import random

            random.shuffle(self.draw_pile)
        card = self.draw_pile.pop()
        self.discard_pile.append(card)
        return card
