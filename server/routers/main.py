from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..paths import WEB_ROOT

router = APIRouter(tags=["main"])

@router.get("/")
async def root():
    return FileResponse(WEB_ROOT / "main" / "index.html")