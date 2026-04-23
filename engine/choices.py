from dataclasses import dataclass, field


@dataclass
class Choice:
    pass


@dataclass
class DeclineBuyPropertyChoice(Choice):
    player_id: int


@dataclass
class BuyPropertyChoice(Choice):
    player_id: int
    property_name: str
    price: int


@dataclass
class PayFineChoice(Choice):
    player_id: int
    fine: int


@dataclass
class TryDoublesJailChoice(Choice):
    player_id: int


@dataclass
class RollDiceChoice(Choice):
    player_id: int


@dataclass
class UseGetOutOfJailFreeCardChoice(Choice):
    player_id: int


@dataclass
class AuctionBidChoice(Choice):
    player_id: int
    tile_position: int
    bid: int


@dataclass
class AuctionPassChoice(Choice):
    player_id: int
    tile_position: int


@dataclass
class MakeTradeOfferChoice(Choice):
    player_id: int
    receiving_player_id: int


@dataclass
class SendTradeOfferChoice(Choice):
    player_id: int
    receiving_player_id: int
    offered_money: int = 0
    requested_money: int = 0
    offered_properties_positions: list[int] = field(default_factory=list)
    requested_properties_positions: list[int] = field(default_factory=list)


@dataclass
class AcceptTradeOfferChoice(Choice):
    player_id: int


@dataclass
class RejectTradeOfferChoice(Choice):
    player_id: int


@dataclass
class BuyImprovementChoice(Choice):
    player_id: int
    property_position: int
    price: int


@dataclass
class SellImprovementChoice(Choice):
    player_id: int
    property_position: int
    price: int


@dataclass
class MortgagePropertyChoice(Choice):
    player_id: int
    property_position: int
    mortgage_value: int


@dataclass
class UnmortgagePropertyChoice(Choice):
    player_id: int
    property_position: int
    unmortgage_value: int
