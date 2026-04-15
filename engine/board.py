from dataclasses import dataclass, field

from engine.tiles import Tile, StartTile


@dataclass
class Board:
    tiles: list[Tile]
    start_tiles: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.find_start_tile_positions()

    def get_tile(self, position: int) -> Tile:
        return self.tiles[position]

    def get_tile_position(self, tile: Tile) -> int:
        return self.tiles.index(tile)

    def size(self) -> int:
        return len(self.tiles)

    def find_start_tile_positions(self) -> None:
        self.start_tiles = [
            i for i, tile in enumerate(self.tiles) if isinstance(tile, StartTile)
        ]
        
    def get_group_tiles(self, group_id: int) -> list[Tile]:
        return [tile for tile in self.tiles if hasattr(tile, 'group_id') and tile.group_id == group_id]

