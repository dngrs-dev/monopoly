from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..paths import WEB_ROOT

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/")
async def settings():
    return FileResponse(WEB_ROOT / "settings" / "index.html")