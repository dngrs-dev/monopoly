from dataclasses import dataclass

from cards import Card


@dataclass
class Deck:
    cards: list[Card]
    draw_pile: list[Card] = None
    discard_pile: list[Card] = None

    def draw_card(self) -> Card:
        if not self.draw_pile:
            self.draw_pile = self.cards.copy()
            import random

            random.shuffle(self.draw_pile)
        if not self.draw_pile:
            raise ValueError("No cards left to draw")
        card = self.draw_pile.pop()
        if not self.discard_pile:
            self.discard_pile = []
        self.discard_pile.append(card)
        return card
