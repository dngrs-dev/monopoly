from dataclasses import dataclass


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


@dataclass
class PlayerMoved(Event):
    player_id: int
    from_position: int
    to_position: int
    steps: int = None
    reason: str = None

@dataclass 
class PlayerSkipTurn(Event):
    player_id: int
    turns_left: int = None