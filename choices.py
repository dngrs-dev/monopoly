from dataclasses import dataclass


@dataclass
class Choice:
    pass


@dataclass
class DeclineBuyPropertyChoice(Choice):
    player_id: int


@dataclass
class BuyPropertyChoice(Choice):
    player_id: int
    property_name: str
    price: int


@dataclass
class PayFineChoice(Choice):
    player_id: int
    fine: int


@dataclass
class TryDoublesJailChoice(Choice):
    player_id: int


@dataclass
class RollDiceChoice(Choice):
    player_id: int
    
@dataclass
class UseGetOutOfJailFreeCardChoice(Choice):
    player_id: int
