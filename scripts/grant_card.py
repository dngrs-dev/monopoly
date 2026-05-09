"""
CLI script to grant a card to a user.
Usage: python grant_card.py <user_id> <card_id> [--inv-db /path/to/inventory.db]
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.inventory_db import InventoryDb


def grant_card(user_id: str, card_id: str, inv_db_path: str) -> None:
    """Grant a card to a user."""
    db = InventoryDb(inv_db_path)
    
    # Verify the card exists
    card = db.get_card(card_id=card_id, language_code="en")
    if not card:
        print(f"❌ Card '{card_id}' not found!")
        sys.exit(1)
    
    # Grant the card
    instance_id = db.grant_card_to_user(user_id=user_id, card_def_id=card_id)
    
    print(f"✅ Granted card to user!")
    print(f"   User ID: {user_id}")
    print(f"   Card: {card['name']} ({card['rarity']['name']})")
    print(f"   Instance ID: {instance_id}")


def main():
    parser = argparse.ArgumentParser(description="Grant a card to a user")
    parser.add_argument("user_id", help="User ID to grant card to")
    parser.add_argument("card_id", help="Card definition ID to grant")
    parser.add_argument(
        "--inv-db",
        type=str,
        default=".data/inventory.db",
        help="Path to inventory database (default: .data/inventory.db)",
    )
    args = parser.parse_args()

    grant_card(args.user_id, args.card_id, args.inv_db)


if __name__ == "__main__":
    main()
