import os
import re
from datetime import datetime, timezone
from typing import Generator

import secrets
from passlib.context import CryptContext
from sqlalchemy import DateTime, BigInteger, String, create_engine, select, Boolean, Float, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker, relationship

from .paths import DB_PATH

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    profile_link: Mapped[str] = mapped_column(String)
    avatar_url: Mapped[str] = mapped_column(String)
    points: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
class Rarity(Base):
    __tablename__ = "rarities"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String)
    multiplier: Mapped[float] = mapped_column(Float)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
class MultiplierCard(Base):
    __tablename__ = "multiplier_cards"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rarity_id: Mapped[int] = mapped_column(ForeignKey("rarities.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    image_url: Mapped[str] = mapped_column(String)
    points_cost: Mapped[int] = mapped_column(BigInteger, default=0)
    available_shop: Mapped[bool] = mapped_column(Boolean, default=False)
    available_market: Mapped[bool] = mapped_column(Boolean, default=False)
    tradeable: Mapped[bool] = mapped_column(Boolean, default=False)
    
    rarity: Mapped[Rarity] = relationship()
    
class UserMultiplierCard(Base):
    __tablename__ = "user_multiplier_cards"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    card_id: Mapped[int] = mapped_column(ForeignKey("multiplier_cards.id"))
    source: Mapped[str] = mapped_column(String, default="point_shop")
    tradeable: Mapped[bool] = mapped_column(Boolean, default=False)
    sellable: Mapped[bool] = mapped_column(Boolean, default=False)
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    definition: Mapped[MultiplierCard] = relationship()
    
class PointTransaction(Base):
    __tablename__ = "point_transactions"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(String)
    related_card_instance_id: Mapped[int | None] = mapped_column(ForeignKey("user_multiplier_cards.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
DEFAULT_AVATAR_URL = "/avatars/default_avatar.png"
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_slug_regex = re.compile(r'[^a-z0-9]+')

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def generate_unique_user_id(db: Session) -> int:
    while True:
        candidate = secrets.randbelow(9_000_000_000_000_000) + 1_000_000_000_000_000
        exists = db.execute(select(User.id).where(User.id == candidate)).first()
        if not exists:
            return candidate
        
def hash_password(password: str) -> str:
    return _pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)

def make_profile_link(seed: str, db: Session) -> str:
    base = _slug_regex.sub('-', seed.lower()).strip('-')
    candidate = base
    suffix = 1
    while db.execute(select(User).where(User.profile_link == candidate)).first():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate

if __name__ == "__main__":
    generate_unique_user_id(SessionLocal())