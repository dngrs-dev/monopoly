import { state, setStatus, setError } from "./context.js";
import { renderAuthState, renderCurrentLobby, renderLobbyList } from "./render.js";
import { handleMessage } from "./handlers.js";

export function disconnectWs() {
  if (state.ws) {
    try {
      state.ws.close();
    } catch {}
  }
  state.ws = null;
  setStatus("disconnected");
}

export function connectWs() {
  if (!state.authed) return;
  if (
    state.ws &&
    (state.ws.readyState === WebSocket.OPEN ||
      state.ws.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }

  const url = new URL(window.location.href);
  const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProto}//${url.host}/ws`;
  state.ws = new WebSocket(wsUrl);

  state.ws.onopen = () => {
    setStatus("connected");
    setError("");
    renderAuthState();
    renderLobbyList();
    renderCurrentLobby();
    state.ws?.send(JSON.stringify({ type: "lobby_list" }));
  };

  state.ws.onmessage = (evt) => {
    try {
      handleMessage(JSON.parse(evt.data));
    } catch {
      setError("Bad JSON from server");
    }
  };

  state.ws.onclose = () => {
    setStatus("disconnected");
    renderAuthState();
    renderLobbyList();
    renderCurrentLobby();
  };

  state.ws.onerror = () => {
    setError("WebSocket error");
  };
}
