from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependecies import User, get_db
from ..jwt_utils import get_current_user_optional
from ..paths import WEB_ROOT

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/")
def my_profile(current_user: User | None = Depends(get_current_user_optional)):
    if not current_user:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/profile/{current_user.profile_link}", status_code=303)

@router.get("/{profile_link}")
def profile_page(profile_link: str):
    return FileResponse(WEB_ROOT / "profile" / "index.html")


class PublicProfile(BaseModel):
    display_name: str
    profile_link: str
    avatar_url: str
    
@router.get("/api/{profile_link}", response_model=PublicProfile)
def get_public_profile(profile_link: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.profile_link == profile_link))
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    return PublicProfile(
        display_name=user.display_name,
        profile_link=user.profile_link,
        avatar_url=user.avatar_url
    )