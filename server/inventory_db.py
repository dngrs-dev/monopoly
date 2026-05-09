from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List
from uuid import uuid4
from datetime import datetime, timezone


@dataclass
class EquippedRentCard:
    id: str
    user_id: str
    card_instance_id: str
    board_id: str
    multiplier: float
    target_positions: list[int] | None
    target_group_id: int | None
    equipped_at: str


@dataclass
class CardDef:
    id: str
    image_path: str
    rarity_id: str


@dataclass
class CardI18n:
    id: str
    card_id: str
    language_code: str
    name: str
    description: str


@dataclass
class RarityDef:
    id: str
    color: str


@dataclass
class RarityI18n:
    id: str
    rarity_id: str
    language_code: str
    name: str


class InventoryDb:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_cards (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    card_def_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS equipped_cards (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    card_instance_id TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    multiplier REAL NOT NULL,
                    target_group_id INTEGER,
                    equipped_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_equipped_card_instance ON equipped_cards(card_instance_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_equipped_user_board ON equipped_cards(user_id, board_id);")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS equipped_positions (
                    id TEXT PRIMARY KEY,
                    equip_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY(equip_id) REFERENCES equipped_cards(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_board_position ON equipped_positions(user_id, board_id, position);")
            # Card definition tables
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rarities (
                    id TEXT PRIMARY KEY,
                    color TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rarity_i18n (
                    id TEXT PRIMARY KEY,
                    rarity_id TEXT NOT NULL,
                    language_code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY(rarity_id) REFERENCES rarities(id) ON DELETE CASCADE,
                    UNIQUE(rarity_id, language_code)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    image_path TEXT NOT NULL,
                    rarity_id TEXT NOT NULL,
                    FOREIGN KEY(rarity_id) REFERENCES rarities(id)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS card_i18n (
                    id TEXT PRIMARY KEY,
                    card_id TEXT NOT NULL,
                    language_code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
                    UNIQUE(card_id, language_code)
                );
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_equipped_for_user_board(self, user_id: str, board_id: str) -> List[EquippedRentCard]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM equipped_cards WHERE user_id = ? AND board_id = ?",
                (user_id, board_id),
            ).fetchall()

            result: list[EquippedRentCard] = []
            for row in rows:
                pos_rows = conn.execute(
                    "SELECT position FROM equipped_positions WHERE equip_id = ?",
                    (row["id"],),
                ).fetchall()
                positions = [int(r["position"]) for r in pos_rows] if pos_rows else None
                result.append(
                    EquippedRentCard(
                        id=str(row["id"]),
                        user_id=str(row["user_id"]),
                        card_instance_id=str(row["card_instance_id"]),
                        board_id=str(row["board_id"]),
                        multiplier=float(row["multiplier"]),
                        target_positions=positions,
                        target_group_id=(row["target_group_id"] if row["target_group_id"] is not None else None),
                        equipped_at=str(row["equipped_at"]),
                    )
                )

        return result

    def equip_card(
        self,
        *,
        user_id: str,
        card_instance_id: str,
        board_id: str,
        multiplier: float,
        target_positions: list[int] | None,
        target_group_id: int | None,
    ) -> str:
        # enforce constraints: card_instance not already equipped; positions unique per user+board
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            # ensure card_instance exists and belongs to user
            owner_row = conn.execute(
                "SELECT id FROM user_cards WHERE id = ? AND user_id = ?",
                (card_instance_id, user_id),
            ).fetchone()
            if not owner_row:
                raise ValueError("Card instance not found or not owned by user")

            # check card_instance already equipped
            row = conn.execute(
                "SELECT id FROM equipped_cards WHERE card_instance_id = ?",
                (card_instance_id,),
            ).fetchone()
            if row:
                raise ValueError("Card instance already equipped")

            # load existing positions for user+board to check conflicts
            pos_rows = conn.execute(
                "SELECT p.position FROM equipped_positions p JOIN equipped_cards e ON p.equip_id = e.id WHERE e.user_id = ? AND e.board_id = ?",
                (user_id, board_id),
            ).fetchall()
            existing_positions: set[int] = {int(r["position"]) for r in pos_rows} if pos_rows else set()

            if target_positions:
                for p in target_positions:
                    if int(p) in existing_positions:
                        raise ValueError(f"Position {p} already has an equipped card for this user and board")

            equip_id = uuid4().hex
            conn.execute(
                "INSERT INTO equipped_cards (id, user_id, card_instance_id, board_id, multiplier, target_group_id, equipped_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (equip_id, user_id, card_instance_id, board_id, float(multiplier), target_group_id, now),
            )
            # insert positions rows
            if target_positions:
                for pos in target_positions:
                    pos_id = uuid4().hex
                    conn.execute(
                        "INSERT INTO equipped_positions (id, equip_id, user_id, board_id, position) VALUES (?, ?, ?, ?, ?)",
                        (pos_id, equip_id, user_id, board_id, int(pos)),
                    )
            conn.commit()
        return equip_id

    def unequip_card(self, *, user_id: str, card_instance_id: str | None = None, equip_id: str | None = None) -> int:
        if not card_instance_id and not equip_id:
            raise ValueError("Either card_instance_id or equip_id must be provided")
        with self._connect() as conn:
            if equip_id:
                res = conn.execute(
                    "DELETE FROM equipped_cards WHERE id = ? AND user_id = ?",
                    (equip_id, user_id),
                )
            else:
                res = conn.execute(
                    "DELETE FROM equipped_cards WHERE card_instance_id = ? AND user_id = ?",
                    (card_instance_id, user_id),
                )
            conn.commit()
            return res.rowcount

    def create_rarity(self, *, rarity_id: str, color: str) -> RarityDef:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO rarities (id, color) VALUES (?, ?)",
                (rarity_id, color),
            )
            conn.commit()
        return RarityDef(id=rarity_id, color=color)

    def set_rarity_i18n(self, *, rarity_id: str, language_code: str, name: str) -> str:
        i18n_id = uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO rarity_i18n (id, rarity_id, language_code, name) VALUES (?, ?, ?, ?)",
                (i18n_id, rarity_id, language_code, name),
            )
            conn.commit()
        return i18n_id

    def create_card(self, *, card_id: str, image_path: str, rarity_id: str) -> CardDef:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO cards (id, image_path, rarity_id) VALUES (?, ?, ?)",
                (card_id, image_path, rarity_id),
            )
            conn.commit()
        return CardDef(id=card_id, image_path=image_path, rarity_id=rarity_id)

    def set_card_i18n(self, *, card_id: str, language_code: str, name: str, description: str) -> str:
        i18n_id = uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO card_i18n (id, card_id, language_code, name, description) VALUES (?, ?, ?, ?, ?)",
                (i18n_id, card_id, language_code, name, description),
            )
            conn.commit()
        return i18n_id

    def get_card(self, *, card_id: str, language_code: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT c.id, ci.name, ci.description, c.image_path, 
                       r.id as rarity_id, ri.name as rarity_name, r.color
                FROM cards c
                JOIN card_i18n ci ON c.id = ci.card_id
                JOIN rarities r ON c.rarity_id = r.id
                JOIN rarity_i18n ri ON r.id = ri.rarity_id
                WHERE c.id = ? AND ci.language_code = ? AND ri.language_code = ?
                """,
                (card_id, language_code, language_code),
            ).fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "description": str(row["description"]),
            "image_path": str(row["image_path"]),
            "rarity": {
                "id": str(row["rarity_id"]),
                "name": str(row["rarity_name"]),
                "color": str(row["color"]),
            },
        }

    def list_cards(self, *, language_code: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, ci.name, ci.description, c.image_path, 
                       r.id as rarity_id, ri.name as rarity_name, r.color
                FROM cards c
                JOIN card_i18n ci ON c.id = ci.card_id
                JOIN rarities r ON c.rarity_id = r.id
                JOIN rarity_i18n ri ON r.id = ri.rarity_id
                WHERE ci.language_code = ? AND ri.language_code = ?
                ORDER BY c.id
                """,
                (language_code, language_code),
            ).fetchall()
        result = []
        for row in rows:
            result.append({
                "id": str(row["id"]),
                "name": str(row["name"]),
                "description": str(row["description"]),
                "image_path": str(row["image_path"]),
                "rarity": {
                    "id": str(row["rarity_id"]),
                    "name": str(row["rarity_name"]),
                    "color": str(row["color"]),
                },
            })
        return result

    def grant_card_to_user(self, *, user_id: str, card_def_id: str) -> str:
        """Grant a card definition to a user. Returns the card instance ID."""
        card_instance_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO user_cards (id, user_id, card_def_id, acquired_at) VALUES (?, ?, ?, ?)",
                (card_instance_id, user_id, card_def_id, now),
            )
            conn.commit()
        return card_instance_id

    def list_user_cards(self, *, user_id: str, language_code: str) -> list[dict]:
        """List all cards owned by a user with translations."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT uc.id, c.id as card_id, ci.name, ci.description, c.image_path,
                       r.id as rarity_id, ri.name as rarity_name, r.color,
                       uc.acquired_at
                FROM user_cards uc
                JOIN cards c ON uc.card_def_id = c.id
                JOIN card_i18n ci ON c.id = ci.card_id
                JOIN rarities r ON c.rarity_id = r.id
                JOIN rarity_i18n ri ON r.id = ri.rarity_id
                WHERE uc.user_id = ? AND ci.language_code = ? AND ri.language_code = ?
                ORDER BY uc.acquired_at DESC
                """,
                (user_id, language_code, language_code),
            ).fetchall()
        result = []
        for row in rows:
            result.append({
                "instance_id": str(row["id"]),
                "card_id": str(row["card_id"]),
                "name": str(row["name"]),
                "description": str(row["description"]),
                "image_path": str(row["image_path"]),
                "rarity": {
                    "id": str(row["rarity_id"]),
                    "name": str(row["rarity_name"]),
                    "color": str(row["color"]),
                },
                "acquired_at": str(row["acquired_at"]),
            })
        return result


# convenience singleton for the server to import
inventory_db: InventoryDb | None = None

def init(path: str | Path):
    global inventory_db
    inventory_db = InventoryDb(path)
    inventory_db.init()
