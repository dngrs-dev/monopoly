from __future__ import annotations

import base64
import hashlib
import hmac
import itertools
import secrets
import sqlite3
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PBKDF2_NAME = "pbkdf2_sha256"
PBKDF2_HASH_NAME = "sha256"
PBKDF2_ITERATIONS = 210_000
PBKDF2_SALT_BYTES = 16
PBKDF2_DKLEN = 32
USERNAME_MAX_LENGTH = 32
HANDLE_MAX_LENGTH = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        PBKDF2_HASH_NAME,
        password_bytes,
        salt,
        PBKDF2_ITERATIONS,
        dklen=PBKDF2_DKLEN,
    )

    return f"{PBKDF2_NAME}${PBKDF2_ITERATIONS}${_b64e(salt)}${_b64e(derived)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        name, iters_s, salt_b64, derived_b64 = stored_hash.split("$", 3)
        if name != PBKDF2_NAME:
            return False

        iterations = int(iters_s)
        if iterations <= 0:
            return False

        salt = _b64d(salt_b64)
        expected = _b64d(derived_b64)
    except Exception:
        return False

    password_bytes = password.encode("utf-8")
    actual = hashlib.pbkdf2_hmac(
        PBKDF2_HASH_NAME,
        password_bytes,
        salt,
        iterations,
        dklen=len(expected),
    )

    return hmac.compare_digest(actual, expected)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    return username.strip()


def normalize_handle(handle: str) -> str:
    base = handle.strip().lower()
    allowed = set(string.ascii_lowercase + string.digits + "_")
    cleaned: list[str] = []
    for ch in base:
        if ch in allowed:
            cleaned.append(ch)
        elif ch in {" ", "-", "."}:
            cleaned.append("_")
    result = "".join(cleaned).strip("_")
    if not result:
        result = "user"
    return result[:HANDLE_MAX_LENGTH]


def default_username_from_email(email: str) -> str:
    local = normalize_email(email).partition("@")[0]
    allowed = set(string.ascii_lowercase + string.digits + "._-")
    filtered = "".join(ch for ch in local if ch in allowed)
    base = filtered.strip("._-")
    if not base:
        base = "user"
    return base[:USERNAME_MAX_LENGTH]


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    username: str
    handle: str
    password_hash: str
    created_at: str


class AuthDb:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    username TEXT NOT NULL UNIQUE,
                    handle TEXT,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(users);").fetchall()
            }
            if "handle" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN handle TEXT;")

            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_handle ON users(handle);"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS username_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_username_history_user ON username_history(user_id, id DESC);"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY,
                    games_played INTEGER NOT NULL,
                    wins INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )

            rows = conn.execute(
                "SELECT id, username, handle, created_at FROM users"
            ).fetchall()
            for row in rows:
                if not row["handle"]:
                    handle = self._allocate_handle(
                        conn, normalize_handle(str(row["username"]))
                    )
                    conn.execute(
                        "UPDATE users SET handle = ? WHERE id = ?",
                        (handle, row["id"]),
                    )

                history_count = conn.execute(
                    "SELECT COUNT(*) FROM username_history WHERE user_id = ?",
                    (row["id"],),
                ).fetchone()[0]
                if history_count == 0:
                    conn.execute(
                        "INSERT INTO username_history (user_id, username, changed_at) VALUES (?, ?, ?)",
                        (row["id"], row["username"], row["created_at"]),
                    )

                conn.execute(
                    "INSERT OR IGNORE INTO user_stats (user_id, games_played, wins) VALUES (?, 0, 0)",
                    (row["id"],),
                )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(
            id=str(row["id"]),
            email=str(row["email"]),
            username=str(row["username"]),
            handle=str(row["handle"]),
            password_hash=str(row["password_hash"]),
            created_at=str(row["created_at"]),
        )

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, username, handle, password_hash, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        email_norm = normalize_email(email)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, username, handle, password_hash, created_at FROM users WHERE email = ?",
                (email_norm,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_handle(self, handle: str) -> User | None:
        handle_norm = normalize_handle(handle)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, username, handle, password_hash, created_at FROM users WHERE handle = ?",
                (handle_norm,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    @staticmethod
    def _username_candidates(base: str):
        yield base
        for i in itertools.count(1):
            suffix = str(i)
            head = base[: max(1, USERNAME_MAX_LENGTH - len(suffix))]
            yield f"{head}{suffix}"

    @staticmethod
    def _handle_candidates(base: str):
        yield base
        for i in itertools.count(1):
            suffix = str(i)
            head = base[: max(1, HANDLE_MAX_LENGTH - len(suffix))]
            yield f"{head}{suffix}"

    def _allocate_handle(self, conn: sqlite3.Connection, base: str) -> str:
        for candidate in self._handle_candidates(base):
            exists = conn.execute(
                "SELECT 1 FROM users WHERE handle = ?", (candidate,)
            ).fetchone()
            if not exists:
                return candidate
        raise RuntimeError("Failed to allocate a unique handle")

    def create_user(
        self, *, email: str, password: str, username: str | None = None
    ) -> User:
        email_norm = normalize_email(email)
        if self.get_user_by_email(email_norm):
            raise ValueError("Email already exists")

        username_base = (
            normalize_username(username)
            if username is not None
            else default_username_from_email(email_norm)
        )
        if not (1 <= len(username_base) <= USERNAME_MAX_LENGTH):
            raise ValueError(
                f"Username must be between 1 and {USERNAME_MAX_LENGTH} characters"
            )

        candidates = [username_base]
        if username is None:
            candidates = self._username_candidates(username_base)

        password_hash = hash_password(password)

        with self._connect() as conn:
            for candidate in candidates:
                user_id = uuid4().hex
                created_at = _utcnow().isoformat()
                handle = self._allocate_handle(conn, normalize_handle(candidate))
                try:
                    conn.execute(
                        "INSERT INTO users (id, email, username, handle, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            user_id,
                            email_norm,
                            candidate,
                            handle,
                            password_hash,
                            created_at,
                        ),
                    )
                    conn.execute(
                        "INSERT INTO username_history (user_id, username, changed_at) VALUES (?, ?, ?)",
                        (user_id, candidate, created_at),
                    )
                    conn.execute(
                        "INSERT INTO user_stats (user_id, games_played, wins) VALUES (?, 0, 0)",
                        (user_id,),
                    )
                    conn.commit()
                    return User(
                        id=user_id,
                        email=email_norm,
                        username=candidate,
                        handle=handle,
                        password_hash=password_hash,
                        created_at=created_at,
                    )
                except sqlite3.IntegrityError as e:
                    message = str(e).lower()
                    if "users.email" in message:
                        raise ValueError("Email already exists") from e
                    if "users.username" in message and username is None:
                        continue
                    raise ValueError("Username already exists") from e

        raise RuntimeError("Failed to allocate a unique username")

    def update_username(self, *, user_id: str, username: str) -> User:
        username_norm = normalize_username(username)
        if not (1 <= len(username_norm) <= USERNAME_MAX_LENGTH):
            raise ValueError(
                f"Username must be between 1 and {USERNAME_MAX_LENGTH} characters"
            )

        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "UPDATE users SET username = ? WHERE id = ?",
                    (username_norm, user_id),
                )
                conn.execute(
                    "INSERT INTO username_history (user_id, username, changed_at) VALUES (?, ?, ?)",
                    (user_id, username_norm, _utcnow().isoformat()),
                )
                conn.execute(
                    "DELETE FROM username_history WHERE id IN ("
                    "SELECT id FROM username_history WHERE user_id = ? ORDER BY id DESC LIMIT -1 OFFSET 10"
                    ")",
                    (user_id,),
                )
                conn.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError("Username already exists") from e

        if cursor.rowcount == 0:
            raise ValueError("User not found")

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    def get_username_history(self, user_id: str) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT username, changed_at FROM username_history WHERE user_id = ? ORDER BY id DESC LIMIT 10",
                (user_id,),
            ).fetchall()
        return [
            {"username": str(row["username"]), "changed_at": str(row["changed_at"])}
            for row in rows
        ]

    def get_user_stats(self, user_id: str) -> dict[str, int]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT games_played, wins FROM user_stats WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO user_stats (user_id, games_played, wins) VALUES (?, 0, 0)",
                    (user_id,),
                )
                conn.commit()
                return {"games_played": 0, "wins": 0}
        return {"games_played": int(row["games_played"]), "wins": int(row["wins"])}

    def authenticate(self, *, email: str, password: str) -> User | None:
        user = self.get_user_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user
