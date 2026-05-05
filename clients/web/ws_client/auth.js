import { state, setError } from "./context.js";
import { renderAuthState, renderCurrentLobby, renderLobbyList } from "./render.js";
import { connectWs, disconnectWs } from "./ws.js";

export async function checkAuth() {
  setError("");
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (!res.ok) {
      state.authed = false;
      state.currentUser = null;
      renderAuthState();
      renderLobbyList();
      renderCurrentLobby();
      disconnectWs();
      return;
    }

    state.currentUser = await res.json().catch(() => null);
    state.authed = !!state.currentUser;
  } catch {
    state.authed = false;
    state.currentUser = null;
  }

  renderAuthState();
  renderLobbyList();
  renderCurrentLobby();
  if (state.authed) connectWs();
}
