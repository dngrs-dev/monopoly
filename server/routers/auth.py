from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..jwt_utils import (
    create_access_token,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_user
)

from ..dependecies import (
    DEFAULT_AVATAR_URL,
    User,
    get_db,
    hash_password,
    make_profile_link,
    verify_password,
    generate_unique_user_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    display_name: str
    profile_link: str
    avatar_url: str
    
def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))

@router.post("/register", response_model=UserOut)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if _get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    display_name = email.split("@")[0]
    profile_link = make_profile_link(display_name, db)
    
    user = User(
        id=generate_unique_user_id(db),
        email=email,
        password_hash=hash_password(payload.password),
        display_name=display_name,
        profile_link=profile_link,
        avatar_url=DEFAULT_AVATAR_URL
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(user.id)
    set_auth_cookie(response, token)
    return user

@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = _get_user_by_email(db, email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(user.id)
    set_auth_cookie(response, token)
    return user

@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/session", response_model=UserOut)
def session(current_user: User = Depends(get_current_user)):
    return current_user