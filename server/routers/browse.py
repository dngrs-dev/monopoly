from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..paths import WEB_ROOT

router = APIRouter(prefix="/browse", tags=["browse"])

@router.get("/")
async def browse():
    return FileResponse(WEB_ROOT / "browse" / "index.html")