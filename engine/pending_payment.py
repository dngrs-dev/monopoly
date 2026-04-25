from dataclasses import dataclass


@dataclass
class PendingPayment:
    debtor_player_id: int
    amount: int
    creditor_player_id: int | None = None  # None means "bank"
    reason: str | None = None
    property_name: str | None = None