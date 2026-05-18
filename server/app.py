from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .dependecies import init_db
from .routers import main, auth, login, signup, profile, ws, settings, avatars, lobbies, browse
from .paths import WEB_ROOT, AVATARS_DIR

load_dotenv()
app = FastAPI()

app.mount("/static", StaticFiles(directory=str(WEB_ROOT), html=True), name="web")
app.include_router(main.router)
app.include_router(auth.router)
app.include_router(login.router)
app.include_router(signup.router)
app.include_router(profile.router)
app.include_router(ws.router)
app.include_router(settings.router)
app.include_router(avatars.router)
app.include_router(lobbies.router)
app.include_router(browse.router)

@app.on_event("startup")
async def _startup():
    init_db()
    print("Starting up...")
    
@app.on_event("shutdown")
async def _shutdown():
    print("Shutting down...")
    
@app.get("/favicon.ico")
async def favicon():
    return FileResponse(WEB_ROOT / "favicon.ico")
    
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return FileResponse(WEB_ROOT / "404" / "index.html", status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")