"""
CLI script to seed sample card definitions and translations into the inventory database.
Usage: python seed_cards.py [--db-path /path/to/inventory.db]
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.inventory_db import InventoryDb


SAMPLE_RARITIES = [
    {
        "id": "common",
        "color": "#888888",
        "i18n": {
            "en": "Common",
            "es": "Común",
            "fr": "Commun",
        },
    },
    {
        "id": "rare",
        "color": "#4169E1",
        "i18n": {
            "en": "Rare",
            "es": "Raro",
            "fr": "Rare",
        },
    },
    {
        "id": "epic",
        "color": "#9932CC",
        "i18n": {
            "en": "Epic",
            "es": "Épico",
            "fr": "Épique",
        },
    },
    {
        "id": "legendary",
        "color": "#FFD700",
        "i18n": {
            "en": "Legendary",
            "es": "Legendario",
            "fr": "Légendaire",
        },
    },
]

SAMPLE_CARDS = [
    {
        "id": "card_001",
        "image_path": "assets/cards/card_001.png",
        "rarity_id": "rare",
        "i18n": {
            "en": {
                "name": "Rent Multiplier +25%",
                "description": "Increases rent collected from properties by 25%",
            },
            "es": {
                "name": "Multiplicador de Alquiler +25%",
                "description": "Aumenta el alquiler recaudado de propiedades en un 25%",
            },
            "fr": {
                "name": "Multiplicateur de Loyer +25%",
                "description": "Augmente le loyer prélevé sur les propriétés de 25%",
            },
        },
    },
    {
        "id": "card_002",
        "image_path": "assets/cards/card_002.png",
        "rarity_id": "epic",
        "i18n": {
            "en": {
                "name": "Rent Multiplier +50%",
                "description": "Increases rent collected from properties by 50%",
            },
            "es": {
                "name": "Multiplicador de Alquiler +50%",
                "description": "Aumenta el alquiler recaudado de propiedades en un 50%",
            },
            "fr": {
                "name": "Multiplicateur de Loyer +50%",
                "description": "Augmente le loyer prélevé sur les propriétés de 50%",
            },
        },
    },
    {
        "id": "card_003",
        "image_path": "assets/cards/card_003.png",
        "rarity_id": "legendary",
        "i18n": {
            "en": {
                "name": "Rent Multiplier +100%",
                "description": "Doubles the rent collected from properties",
            },
            "es": {
                "name": "Multiplicador de Alquiler +100%",
                "description": "Duplica el alquiler recaudado de propiedades",
            },
            "fr": {
                "name": "Multiplicateur de Loyer +100%",
                "description": "Double le loyer prélevé sur les propriétés",
            },
        },
    },
    {
        "id": "card_004",
        "image_path": "assets/cards/card_004.png",
        "rarity_id": "common",
        "i18n": {
            "en": {
                "name": "Rent Multiplier +10%",
                "description": "Increases rent collected from properties by 10%",
            },
            "es": {
                "name": "Multiplicador de Alquiler +10%",
                "description": "Aumenta el alquiler recaudado de propiedades en un 10%",
            },
            "fr": {
                "name": "Multiplicateur de Loyer +10%",
                "description": "Augmente le loyer prélevé sur les propriétés de 10%",
            },
        },
    },
]


def seed_database(db_path: str) -> None:
    """Seed the database with sample card definitions."""
    db = InventoryDb(db_path)
    db.init()

    print(f"Seeding database at {db_path}...")

    # Create rarities
    print("\nCreating rarities...")
    for rarity in SAMPLE_RARITIES:
        rarity_id = rarity["id"]
        color = rarity["color"]
        db.create_rarity(rarity_id=rarity_id, color=color)
        print(f"  Created rarity: {rarity_id}")

        # Add i18n for rarity
        for lang_code, name in rarity["i18n"].items():
            db.set_rarity_i18n(rarity_id=rarity_id, language_code=lang_code, name=name)
            print(f"    Added {lang_code} translation: {name}")

    # Create cards
    print("\nCreating cards...")
    for card in SAMPLE_CARDS:
        card_id = card["id"]
        image_path = card["image_path"]
        rarity_id = card["rarity_id"]
        db.create_card(card_id=card_id, image_path=image_path, rarity_id=rarity_id)
        print(f"  Created card: {card_id}")

        # Add i18n for card
        for lang_code, i18n_data in card["i18n"].items():
            db.set_card_i18n(
                card_id=card_id,
                language_code=lang_code,
                name=i18n_data["name"],
                description=i18n_data["description"],
            )
            print(f"    Added {lang_code} translation: {i18n_data['name']}")

    print("\n✅ Database seeding complete!")

    # Verify
    print("\nVerifying data...")
    cards_en = db.list_cards(language_code="en")
    print(f"  Found {len(cards_en)} cards in English:")
    for card in cards_en:
        print(f"    - {card['name']} ({card['rarity']['name']}, {card['image_path']})")

    cards_es = db.list_cards(language_code="es")
    print(f"  Found {len(cards_es)} cards in Spanish:")
    for card in cards_es:
        print(f"    - {card['name']} ({card['rarity']['name']})")


def main():
    parser = argparse.ArgumentParser(
        description="Seed the inventory database with sample card definitions"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=".data/inventory.db",
        help="Path to inventory database (default: .data/inventory.db)",
    )
    args = parser.parse_args()

    db_path = args.db_path
    seed_database(db_path)


if __name__ == "__main__":
    main()
