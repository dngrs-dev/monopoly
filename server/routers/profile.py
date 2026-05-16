from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse

from ..dependecies import User
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