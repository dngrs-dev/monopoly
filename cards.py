from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from deck import Deck


@dataclass
class Card:
    pass


@dataclass
class MoveToPositionCard(Card):
    position: int


@dataclass
class MoveStepsCard(Card):
    steps: int


@dataclass
class MoneyCard(Card):
    amount: int


@dataclass
class GoToJailCard(Card):
    pass


@dataclass
class GetOutOfJailFreeCard(Card):
    origin_deck: Deck | None = None
