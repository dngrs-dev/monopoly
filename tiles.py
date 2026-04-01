from dataclasses import dataclass
from enum import Enum, auto


class TileType(Enum):
    PROPERTY = auto()
    JAIL = auto()
    MOVE = auto()
    START = auto()
    CHANCE = auto()
    NOTHING = auto()


@dataclass
class Tile:
    name: str
    tile_type: TileType


@dataclass
class PropertyTile(Tile):
    price: int
    rent: int
    owner: int = None


@dataclass
class JailTile(Tile):
    skips: int = 2


@dataclass
class MoveTile(Tile):
    move_to: int


@dataclass
class StartTile(Tile):
    go_bonus: int = 200
    stay_bonus: int = 100


@dataclass
class ChanceTile(Tile):
    pass
