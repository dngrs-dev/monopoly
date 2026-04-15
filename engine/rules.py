from dataclasses import dataclass


@dataclass
class Rules:
    double_rent_on_monopoly: bool = True # Owning all properties in a group doubles the rent for those properties
    auction_enabled: bool = False  # If player declines to buy a property
