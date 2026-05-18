import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
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
    
class LobbyOut(BaseModel):
    lobby_id: str
    host_id: int
    players: list[int]
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
                players=[user_id],
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
        
    async def leave_lobby(self, user_id: int) -> None:
        async with self._lock:
            lobby_id = self._user_to_lobby.get(user_id)
            if not lobby_id:
                raise HTTPException(status_code=404, detail="User is not in a lobby")
            
            lobby = self._lobbies.get(lobby_id)
            if not lobby:
                raise HTTPException(status_code=404, detail="Lobby not found")
            
            lobby.players.discard(user_id)
            self._user_to_lobby.pop(user_id, None)
            
            if not lobby.players:
                self._lobbies.pop(lobby_id, None)
                return
            
            if lobby.host_id == user_id:
                lobby.host_id = next(iter(lobby.players))
                
    async def list_lobbies(self) -> list[Lobby]:
        async with self._lock:
            return list(self._lobbies.values())
        
    async def get_user_lobby(self, user_id: int) -> Lobby | None:
        async with self._lock:
            lobby_id = self._user_to_lobby.get(user_id)
            if not lobby_id:
                return None
            return self._lobbies.get(lobby_id)
        
        
manager = LobbyManager()


@router.post("/create", response_model=LobbyOut, status_code=status.HTTP_201_CREATED)
async def create_lobby(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lobby = await manager.create_lobby(current_user.id)
    return LobbyOut(
        lobby_id=lobby.lobby_id,
        host_id=lobby.host_id,
        players=list(lobby.players),
        max_players=lobby.max_players
    )
    
@router.post("/{lobby_id}/join", response_model=LobbyOut)
async def join_lobby(lobby_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lobby = await manager.join_lobby(current_user.id, lobby_id)
    return LobbyOut(
        lobby_id=lobby.lobby_id,
        host_id=lobby.host_id,
        players=list(lobby.players),
        max_players=lobby.max_players
    )
    
@router.post("/leave")
async def leave_lobby(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    await manager.leave_lobby(current_user.id)
    return {"ok": True}

@router.get("/", response_model=list[LobbyOut])
async def list_lobbies():
    lobbies = await manager.list_lobbies()
    return [
        LobbyOut(
            lobby_id=lobby.lobby_id,
            host_id=lobby.host_id,
            players=list(lobby.players),
            max_players=lobby.max_players
        )
        for lobby in lobbies
    ]
    
@router.get("/me", response_model=LobbyOut | None)
async def my_lobby(current_user: User = Depends(get_current_user)):
    lobby = await manager.get_user_lobby(current_user.id)
    if not lobby:
        return None
    return LobbyOut(
        lobby_id=lobby.lobby_id,
        host_id=lobby.host_id,
        players=list(lobby.players),
        max_players=lobby.max_players
    )