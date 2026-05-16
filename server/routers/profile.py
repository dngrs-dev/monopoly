import os
from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..dependecies import get_db
from ..jwt_utils import JWT_COOKIE_NAME, get_user_from_cookie
from ..paths import WEB_ROOT

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/")
def my_profile(access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    user = get_user_from_cookie(access_token, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/profile/{user.profile_link}", status_code=303)

@router.get("/{profile_link}")
def profile_page(profile_link: str):
    return FileResponse(WEB_ROOT / "profile" / "index.html")