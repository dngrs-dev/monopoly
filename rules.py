from dataclasses import dataclass


@dataclass
class Rules:
    auction_enabled: bool = False  # If player declines to buy a property
