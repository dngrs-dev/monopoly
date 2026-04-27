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
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
            )

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
            password_hash=str(row["password_hash"]),
            created_at=str(row["created_at"]),
        )

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, username, password_hash, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        email_norm = normalize_email(email)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, username, password_hash, created_at FROM users WHERE email = ?",
                (email_norm,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    @staticmethod
    def _username_candidates(base: str):
        yield base
        for i in itertools.count(1):
            suffix = str(i)
            head = base[: max(1, USERNAME_MAX_LENGTH - len(suffix))]
            yield f"{head}{suffix}"

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
                try:
                    conn.execute(
                        "INSERT INTO users (id, email, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                        (user_id, email_norm, candidate, password_hash, created_at),
                    )
                    conn.commit()
                    return User(
                        id=user_id,
                        email=email_norm,
                        username=candidate,
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
                conn.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError("Username already exists") from e

        if cursor.rowcount == 0:
            raise ValueError("User not found")

        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    def authenticate(self, *, email: str, password: str) -> User | None:
        user = self.get_user_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user
