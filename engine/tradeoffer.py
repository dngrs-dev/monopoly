from dataclasses import dataclass


@dataclass
class TradeOffer:
    offering_player_id: int
    receiving_player_id: int
    offered_money: int
    requested_money: int
    offered_properties_positions: list[int]
    requested_properties_positions: list[int]
