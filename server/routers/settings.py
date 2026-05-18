from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..paths import WEB_ROOT
from ..dependecies import User, get_db
from ..jwt_utils import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/")
async def settings():
    return FileResponse(WEB_ROOT / "settings" / "index.html")

@router.get("/check")
async def check(display_name: str = None, profile_link: str = None, db: Session = Depends(get_db)):
    if display_name is not None:
        exists = db.scalar(select(User.id).where(User.display_name == display_name))
        return {"available": not exists}
    elif profile_link is not None:
        exists = db.scalar(select(User.id).where(User.profile_link == profile_link))
        return {"available": not exists}
    else:
        return {"available": False}
    
class UpdateSettings(BaseModel):
    display_name: str = Field(default=None, min_length=2, max_length=64)
    profile_link: str = Field(default=None, min_length=2, max_length=64)
    
@router.patch("/save")
def save_settings(payload: UpdateSettings, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name.strip()
        
    if payload.profile_link is not None:
        link = payload.profile_link.strip()
        exists = db.scalar(select(User.id).where(User.profile_link == link, User.id != current_user.id))
        if exists:
            raise HTTPException(status_code=409, detail="Profile link already taken")
        current_user.profile_link = link
        
    db.commit()
    db.refresh(current_user)
    return {
        "display_name": current_user.display_name,
        "profile_link": current_user.profile_link
    }
        