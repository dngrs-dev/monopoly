from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..paths import WEB_ROOT

router = APIRouter(prefix="/login", tags=["login"])

@router.get("/")
async def login():
    return FileResponse(WEB_ROOT / "login" / "index.html")