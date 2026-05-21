import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependecies import User, get_db
from ..jwt_utils import get_current_user

router = APIRouter(prefix="/lobbies", tags=["lobbies"])

@dataclass
class Lobby:
    lobby_id: str
    host_id: int
    created_at: datetime
    players: set[int] = field(default_factory=set)
    max_players: int = 4
    
class PlayerOut(BaseModel):
    id: int
    display_name: str
    avatar_url: str
    
class LobbyOut(BaseModel):
    lobby_id: str
    host_id: int
    players: list[PlayerOut]
    max_players: int
    
class LobbyManager:
    def __init__(self):
        self._lobbies: dict[str, Lobby] = {}
        self._user_to_lobby: dict[int, str] = {}
        self._lock = asyncio.Lock()
        
    async def create_lobby(self, user_id: int, max_players: int = 4) -> Lobby:
        async with self._lock:
            if user_id in self._user_to_lobby:
                raise HTTPException(status_code=409, detail="User is already in a lobby")
            
            lobby_id = uuid4().hex
            lobby = Lobby(
                lobby_id=lobby_id,
                host_id=user_id,
                created_at=datetime.now(timezone.utc),
                players={user_id},
                max_players=max_players
            )
            
            self._lobbies[lobby_id] = lobby
            self._user_to_lobby[user_id] = lobby_id
            return lobby
        
    async def join_lobby(self, user_id: int, lobby_id: str) -> Lobby:
        async with self._lock:
            if user_id in self._user_to_lobby:
                raise HTTPException(status_code=409, detail="User is already in a lobby")
            
            lobby = self._lobbies.get(lobby_id)
            if not lobby:
                raise HTTPException(status_code=404, detail="Lobby not found")
            
            if len(lobby.players) >= lobby.max_players:
                raise HTTPException(status_code=400, detail="Lobby is full")
            
            lobby.players.add(user_id)
            self._user_to_lobby[user_id] = lobby_id
            return lobby
        
    async def leave_lobby(self, user_id: int) -> tuple[str, bool, int | None]:
        async with self._lock:
            lobby_id = self._user_to_lobby.get(user_id)
            if not lobby_id:
                raise HTTPException(status_code=404, detail="User is not in a lobby")
            
            lobby = self._lobbies.get(lobby_id)
            if not lobby:
                self._user_to_lobby.pop(user_id, None)
                raise HTTPException(status_code=404, detail="Lobby not found")
            
            was_host = lobby.host_id == user_id
            
            lobby.players.discard(user_id)
            self._user_to_lobby.pop(user_id, None)
            
            if not lobby.players:
                self._lobbies.pop(lobby_id, None)
                return lobby_id, True, None
            
            new_host_id = None
            if was_host:
                lobby.host_id = next(iter(lobby.players))
                new_host_id = lobby.host_id
                
            return lobby_id, False, new_host_id
            
                
    async def list_lobbies(self) -> list[Lobby]:
        async with self._lock:
            return list(self._lobbies.values())
        
    async def get_user_lobby(self, user_id: int) -> Lobby | None:
        async with self._lock:
            lobby_id = self._user_to_lobby.get(user_id)
            if not lobby_id:
                return None
            return self._lobbies.get(lobby_id)
        

class LobbyHub:
    def __init__(self) -> None:
        self._connections: set = set()
        self._lock = asyncio.Lock()
        
    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            
    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
            
    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections)
            
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
                
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)
                                        
manager = LobbyManager()
hub = LobbyHub()

def build_lobby_payloads(lobbies: list[Lobby], db: Session) -> list[dict]:
    user_ids = {user_id for lobby in lobbies for user_id in lobby.players}
    if user_ids:
        users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
        user_map = {user.id: user for user in users}
    else:
        user_map = {}
        
    payloads: list[dict] = []
    for lobby in lobbies:
        players = [
            {
                "id": user_id,
                "display_name": user_map[user_id].display_name,
                "avatar_url": user_map[user_id].avatar_url,
            }
            for user_id in lobby.players
            if user_id in user_map
        ]
        payloads.append(
            {
                "lobby_id": lobby.lobby_id,
                "host_id": lobby.host_id,
                "players": players,
                "max_players": lobby.max_players,
            }
        )
    return payloads

@router.post("/create", response_model=LobbyOut, status_code=status.HTTP_201_CREATED)
async def create_lobby(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lobby = await manager.create_lobby(current_user.id)
    payload = build_lobby_payloads([lobby], db)[0]
    await hub.broadcast({"type": "create", "lobby": payload})
    return payload

@router.post("/join/{lobby_id}", response_model=LobbyOut)
async def join_lobby(lobby_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lobby = await manager.join_lobby(current_user.id, lobby_id)
    await hub.broadcast(
        {
            "type": "join",
            "lobby_id": lobby.lobby_id,
            "player": {
                "id": current_user.id,
                "display_name": current_user.display_name,
                "avatar_url": current_user.avatar_url,
            }
        }
    )
    return build_lobby_payloads([lobby], db)[0]

@router.post("/leave")
async def leave_lobby(current_user: User = Depends(get_current_user)):
    lobby_id, removed, new_host_id = await manager.leave_lobby(current_user.id)
    
    if removed:
        await hub.broadcast({"type": "remove", "lobby_id": lobby_id})
    else:
        await hub.broadcast(
            {
                "type": "leave",
                "lobby_id": lobby_id,
                "player_id": current_user.id,
            }
        )
        if new_host_id:
            await hub.broadcast(
                {
                    "type": "host",
                    "lobby_id": lobby_id,
                    "host_id": new_host_id,
                }
            )
    return {"ok": True}

@router.post("/delete")
async def delete_lobby(current_user: User = Depends(get_current_user)):
    lobby = await manager.get_user_lobby(current_user.id)
    if not lobby:
        raise HTTPException(status_code=404, detail="User is not in a lobby")
    
    if lobby.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the host can delete the lobby")
    
    for player_id in list(lobby.players):
        lobby_id, removed, new_host_id = await manager.leave_lobby(current_user.id)
        
        if not removed:
            await hub.broadcast(
                {
                    "type": "leave",
                    "lobby_id": lobby_id
                }
            )
            
    await hub.broadcast({"type": "remove", "lobby_id": lobby.lobby_id})
    
    return {"ok": True}

@router.get("/", response_model=list[LobbyOut])
async def list_lobbies(db: Session = Depends(get_db)):
    lobbies = await manager.list_lobbies()
    return build_lobby_payloads(lobbies, db)

@router.get("/me", response_model=LobbyOut | None)
async def my_lobby(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lobby = await manager.get_user_lobby(current_user.id)
    if not lobby:
        return None
    return build_lobby_payloads([lobby], db)[0]