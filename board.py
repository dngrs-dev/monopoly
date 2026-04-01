from dataclasses import dataclass

from tiles import Tile


@dataclass
class Board:
    tiles: list[Tile]

    def get_tile(self, position: int) -> Tile:
        return self.tiles[position]

    def size(self) -> int:
        return len(self.tiles)
