from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..dependecies import SessionLocal
from ..jwt_utils import get_current_user_optional

router = APIRouter(prefix="/ws", tags=["ws"])

@router.websocket("/echo")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass