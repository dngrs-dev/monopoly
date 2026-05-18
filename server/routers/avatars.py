from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependecies import User, get_db, DEFAULT_AVATAR_URL
from ..jwt_utils import get_current_user

router = APIRouter(prefix="/avatars", tags=["avatars"])

@router.get("/")
def my_avatar(current_user: User = Depends(get_current_user)):
    print(current_user.avatar_url)
    return RedirectResponse(current_user.avatar_url or DEFAULT_AVATAR_URL, status_code=302)


@router.get("/avatars/{profile_link}")
def avatar_by_link(profile_link: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.profile_link == profile_link))
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    return RedirectResponse(user.avatar_url or DEFAULT_AVATAR_URL, status_code=302)