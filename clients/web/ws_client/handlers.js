import { state, setError } from "./context.js";
import { renderAuthState, renderCurrentLobby, renderLobbyList } from "./render.js";

export function handleMessage(data) {
  if (!data) return;

  if (data.type === "error") {
    setError(data.message || "Unknown error");
    return;
  }

  if (data.type === "lobby_list") {
    state.lobbyList = Array.isArray(data.lobbies) ? data.lobbies : [];
    renderLobbyList();
    return;
  }

  if (data.type === "lobby_joined") {
    state.currentLobby = data.lobby || null;
    renderAuthState();
    renderCurrentLobby();
    renderLobbyList();
    return;
  }

  if (data.type === "lobby_update") {
    if (state.currentLobby && data.lobby?.lobby_id === state.currentLobby.lobby_id) {
      state.currentLobby = data.lobby;
      renderCurrentLobby();
    }
    return;
  }

  if (data.type === "lobby_started") {
    const roomId = data.room_id;
    if (roomId) {
      window.location.href = `/game?room=${encodeURIComponent(roomId)}`;
    }
    return;
  }

  if (data.type === "lobby_closed") {
    state.currentLobby = null;
    setError(data.owner_message || data.message || "Lobby closed");
    renderAuthState();
    renderCurrentLobby();
    renderLobbyList();
  }
}
