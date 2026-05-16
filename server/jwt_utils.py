import os
from datetime import datetime, timedelta, timezone

from fastapi import Response, Cookie, Depends, HTTPException
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .dependecies import User, get_db

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALG = "HS256"
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "10080"))
JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "0") == "1"
JWT_COOKIE_NAME = "access_token"
JWT_COOKIE_SAMESITE = "lax"

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_user_id(token: str) -> int | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        return None
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None

def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
        max_age=JWT_EXPIRES_MIN * 60,
    )

def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(JWT_COOKIE_NAME)

def get_user_from_cookie(access_token: str | None, db: Session) -> User | None:
    if not access_token:
        return None
    user_id = decode_user_id(access_token)
    if user_id is None:
        return None
    return db.get(User, user_id)

def get_current_user_optional(access_token: str | None = Cookie(default=None, alias=JWT_COOKIE_NAME), db: Session = Depends(get_db)) -> User | None:
    return get_user_from_cookie(access_token, db)

def get_current_user(access_token: str | None = Cookie(default=None, alias=JWT_COOKIE_NAME), db: Session = Depends(get_db)) -> User:
    user = get_user_from_cookie(access_token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user