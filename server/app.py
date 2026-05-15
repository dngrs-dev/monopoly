from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routers import login
from .routers import main
from .paths import WEB_ROOT

load_dotenv()
app = FastAPI()
app.mount("/static", StaticFiles(directory=str(WEB_ROOT), html=True), name="web")
app.include_router(login.router)
app.include_router(main.router)

@app.on_event("startup")
async def _startup():
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