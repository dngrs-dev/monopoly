from dataclasses import dataclass


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
    pass
