import random

from engine.cards import MoneyCard
from engine.deck import Deck


def test_deck_initializes_discard_pile_from_cards():
    cards = [MoneyCard(amount=1), MoneyCard(amount=2), MoneyCard(amount=3)]
    deck = Deck(cards=cards)

    assert deck.draw_pile == []
    assert deck.discard_pile == cards


def test_deck_draw_refills_and_shuffles_when_empty(monkeypatch):
    cards = [MoneyCard(amount=1), MoneyCard(amount=2), MoneyCard(amount=3)]
    deck = Deck(cards=cards)

    def fake_shuffle(items: list) -> None:
        # Reverse instead of random shuffle
        items.reverse()

    monkeypatch.setattr(random, "shuffle", fake_shuffle)

    drawn = deck.draw_card()

    assert isinstance(drawn, MoneyCard)
    assert drawn.amount == 1
    assert deck.discard_pile == []
    assert len(deck.draw_pile) == 2


def test_deck_discard_appends_to_discard_pile():
    cards = [MoneyCard(amount=1)]
    deck = Deck(cards=cards)

    card = MoneyCard(amount=99)
    deck.discard_card(card)

    assert deck.discard_pile[-1] == card
