from dataclasses import dataclass, field

from cards import Card
from board import Board
from events import (
    Event,
    PlayerPassedStart,
    PlayerLandedOnStart,
)


@dataclass
class Player:
    id: int
    balance: int
    position: int = 0
    skip_turns: int = 0
    bankrupt: bool = False
    in_jail: bool = False
    cards: list[Card] = field(default_factory=list)

    def move_steps(self, steps: int, board: Board) -> list[Event]:
        events: list[Event] = []
        old_position = self.position
        board_size = board.size()
        laps = steps // board_size
        remaining_steps = steps % board_size
        self.position = (self.position + remaining_steps) % board_size

        if steps <= 0:
            return events

        for _ in range(laps):
            for start_pos in board.start_tiles:
                start_tile = board.get_tile(start_pos)
                self.update_balance(start_tile.pass_bonus)
                events.append(
                    PlayerPassedStart(player_id=self.id, amount=start_tile.pass_bonus)
                )

        # Check if player passed or landed on start
        for start_pos in board.start_tiles:
            start_tile = board.get_tile(start_pos)
            if old_position < self.position:
                if old_position < start_pos <= self.position:
                    self.update_balance(start_tile.pass_bonus)
                    events.append(
                        PlayerPassedStart(
                            player_id=self.id, amount=start_tile.pass_bonus
                        )
                    )
                    if self.position == start_pos:
                        self.update_balance(start_tile.land_bonus)
                        events.append(
                            PlayerLandedOnStart(
                                player_id=self.id, amount=start_tile.land_bonus
                            )
                        )

            else:  # Wrapped around the board
                if old_position < start_pos or start_pos <= self.position:
                    self.update_balance(start_tile.pass_bonus)
                    events.append(
                        PlayerPassedStart(
                            player_id=self.id, amount=start_tile.pass_bonus
                        )
                    )
                    if self.position == start_pos:
                        self.update_balance(start_tile.land_bonus)
                        events.append(
                            PlayerLandedOnStart(
                                player_id=self.id, amount=start_tile.land_bonus
                            )
                        )
        return events

    def move_position(self, position: int, board: Board) -> list[Event]:
        old_position = self.position
        target_position = position % board.size()
        steps_forward = (target_position - old_position) % board.size()
        return self.move_steps(steps_forward, board)

    def update_balance(self, amount: int):
        self.balance += amount
