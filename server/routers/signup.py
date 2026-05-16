from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..paths import WEB_ROOT

router = APIRouter(prefix="/signup", tags=["signup"])

@router.get("/")
async def signup():
    return FileResponse(WEB_ROOT / "signup" / "index.html")