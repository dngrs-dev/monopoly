from dataclasses import dataclass

@dataclass
class Command:
    pass

@dataclass
class RollDiceCommand(Command):
    player_id: int