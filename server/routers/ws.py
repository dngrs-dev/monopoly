from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..dependecies import SessionLocal
from ..jwt_utils import JWT_COOKIE_NAME, get_user_from_cookie
from .lobbies import manager, hub, build_lobby_payloads

router = APIRouter(prefix="/ws", tags=["ws"])

@router.websocket("/lobbies")
async def lobby_websocket(websocket: WebSocket):
    db: Session | None = None
    try:
        db = SessionLocal()
        token = websocket.cookies.get(JWT_COOKIE_NAME)
        user = get_user_from_cookie(token, db)
        if not user:
            await websocket.close(code=1008)
            return
        
        await hub.connect(websocket)
        
        lobbies = await manager.list_lobbies()
        await websocket.send_json({"type": "init", "lobbies": build_lobby_payloads(lobbies, db)})
        
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)
        if db is not None:
            db.close()