from dataclasses import dataclass
from enum import Enum, auto


@dataclass
class Event:
    pass


@dataclass
class PlayerLanded(Event):
    player_id: int
    position: int
    tile_name: str


@dataclass
class PlayerPassedStart(Event):
    player_id: int
    amount: int


@dataclass
class PlayerLandedOnStart(Event):
    player_id: int
    amount: int


@dataclass
class PlayerBoughtProperty(Event):
    player_id: int
    property_name: str
    price: int


@dataclass
class PlayerPaidRent(Event):
    player_id: int
    to_player_id: int
    property_name: str
    rent: int


@dataclass
class PlayerWentToJail(Event):
    player_id: int


class MoveReason(Enum):
    ROLL_DICE = auto()
    CARD = auto()
    TILE_EFFECT = auto()
    OTHER = auto()


@dataclass
class PlayerMoved(Event):
    player_id: int
    from_position: int
    to_position: int
    steps: int = None
    reason: MoveReason = None


@dataclass
class PlayerSkipTurn(Event):
    player_id: int
    turns_left: int = None


@dataclass
class PlayerPaidJailFine(Event):
    player_id: int
    amount: int


@dataclass
class PlayerRolledDice(Event):
    player_id: int
    dice1: int
    dice2: int


@dataclass
class PlayerReleasedFromJail(Event):
    player_id: int

@dataclass
class PlayerPaidMoney(Event):
    player_id: int
    amount: int
    reason: str = None
    
@dataclass
class PlayerDrewCard(Event):
    player_id: int
    card_name: str
    
@dataclass
class PlayerUsedGetOutOfJailFreeCard(Event):
    player_id: int
    
@dataclass
class AuctionStarted(Event):
    tile_position: int
    base_price: int
    initial_player_id: int