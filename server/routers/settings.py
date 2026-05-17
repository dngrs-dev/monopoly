from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..paths import WEB_ROOT
from ..dependecies import User, get_db

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