from dataclasses import dataclass
from deck import Deck

@dataclass
class Tile:
    name: str


@dataclass
class PropertyTile(Tile):
    price: int
    rent: int
    owner: int = None


@dataclass
class StartTile(Tile):
    pass_bonus: int = 200
    land_bonus: int = 100


@dataclass
class JailTile(Tile):
    skip_turns: int = 3
    fine: int = 50


@dataclass
class ChanceTile(Tile):
    deck: Deck


@dataclass
class GoToJailTile(Tile):
    pass
