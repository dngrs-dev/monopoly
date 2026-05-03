from dataclasses import dataclass, field


@dataclass
class PendingPayment:
    debtor_player_id: int
    amount: int
    creditor_player_id: int | None = None  # None means "bank"
    reason: str | None = None
    property_position: int | None = None
    per_player_amount: int | None = None
    remaining_player_ids: list[int] = field(default_factory=list)