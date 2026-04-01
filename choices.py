from dataclasses import dataclass

@dataclass
class Choice:
    pass


@dataclass
class BuyPropertyChoice(Choice):
    player_id: int
    property_name: str
    price: int
    
@dataclass
class RollDiceChoice(Choice):
    player_id: int