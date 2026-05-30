from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import select

from server.routers.games import game_sessions, game_hub
from ..dependecies import SessionLocal, User, DEFAULT_AVATAR_URL
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
            
            

async def _send_choices(lobby_id: str, session) -> None:
    user_map = await game_hub.snapshot(lobby_id)
    for user_id, sockets in user_map.items():
        payload = {
            "type": "choices",
            "choices": session.serialize_choices_for_user(user_id),
        }
        for ws in list(sockets):
            try:
                await ws.send_json(payload)
            except Exception:
                pass

BOARD_EVENT_TYPES = {
    "PlayerBoughtProperty",
    "PlayerBoughtImprovement",
    "PlayerSoldProperty",
    "PlayerSoldImprovement",
    "PlayerMortgagedProperty",
    "PlayerUnmortgagedProperty",
}

@router.websocket("/games/{lobby_id}")
async def game_websocket(websocket: WebSocket, lobby_id: str):
    db: Session | None = None
    try:
        db = SessionLocal()
        token = websocket.cookies.get(JWT_COOKIE_NAME)
        user = get_user_from_cookie(token, db)
        if not user:
            await websocket.close(code=1008)
            return

        session = await game_sessions.get(lobby_id)
        if not session or user.id not in session.user_to_player:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        await game_hub.add(lobby_id, user.id, websocket)

        await websocket.send_json(
            {
                "type": "init",
                "player_id": session.user_to_player[user.id],
                "state": session.serialize_state(),
                "choices": session.serialize_choices_for_user(user.id),
                "board": session.serialize_board(),
                "player_meta": session.build_player_meta(db=db),
            }
        )

        while True:
            msg = await websocket.receive_json()
            if msg.get("type") != "choice":
                continue

            events = await session.apply_choice_payload(user.id, msg.get("choice", {}))
            await game_hub.broadcast(
                lobby_id,
                {
                    "type": "state",
                    "events": session.serialize_events(events),
                    "state": session.serialize_state(),
                },
            )
            
            if any(e.__class__.__name__ in BOARD_EVENT_TYPES for e in events):
                await game_hub.broadcast(
                    lobby_id,
                    {
                        "type": "board",
                        "board": session.serialize_board(),
                    },
                )
            await _send_choices(lobby_id, session)

    except WebSocketDisconnect:
        pass
    finally:
        await game_hub.remove(lobby_id, user.id, websocket)
        if db is not None:
            db.close()