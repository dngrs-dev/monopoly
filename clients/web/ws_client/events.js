import { elements, state, setError, isWsReady } from "./context.js";
import { clampLobbyLimit } from "./utils.js";
import { renderAuthState, renderCurrentLobby, renderLobbyList } from "./render.js";
import { checkAuth } from "./auth.js";
import { disconnectWs } from "./ws.js";

export function wireEvents() {
  if (elements.loginBtn) {
    elements.loginBtn.onclick = () => {
      window.location.href = "/login";
    };
  }

  if (elements.profileBtn) {
    elements.profileBtn.onclick = () => {
      const handle = state.currentUser?.handle || "";
      window.location.href = handle ? `/profile/${handle}` : "/profile";
    };
  }

  if (elements.logoutBtn) {
    elements.logoutBtn.onclick = async () => {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          credentials: "same-origin",
        });
      } catch {}

      setError("");
      state.authed = false;
      state.currentUser = null;
      state.lobbyList = [];
      state.currentLobby = null;
      disconnectWs();
      renderAuthState();
      renderLobbyList();
      renderCurrentLobby();
    };
  }

  if (elements.createLobbyBtn) {
    elements.createLobbyBtn.onclick = async () => {
      setError("");
      await checkAuth();
      if (!state.authed || !isWsReady() || state.currentLobby) return;

      const raw = parseInt(elements.lobbyLimitInput?.value ?? "", 10);
      const limit = clampLobbyLimit(raw);
      const visibility = elements.lobbyVisibilitySelect?.value || "public";
      const isPublic = visibility !== "private";

      state.ws?.send(
        JSON.stringify({
          type: "lobby_create",
          user_limit: limit,
          is_public: isPublic,
        }),
      );
    };
  }

  if (elements.startLobbyBtn) {
    elements.startLobbyBtn.onclick = () => {
      if (!isWsReady() || !state.currentLobby?.lobby_id) return;
      state.ws?.send(
        JSON.stringify({
          type: "lobby_start",
          lobby_id: state.currentLobby.lobby_id,
        }),
      );
    };
  }

  if (elements.joinPrivateBtn) {
    elements.joinPrivateBtn.onclick = () => {
      if (!isWsReady() || state.currentLobby) return;
      const inviteCode = (elements.inviteCodeInput?.value || "").trim();
      if (!inviteCode) {
        setError("Invite code is required");
        return;
      }
      state.ws?.send(
        JSON.stringify({
          type: "lobby_join_invite",
          invite_code: inviteCode,
        }),
      );
    };
  }

  if (elements.leaveLobbyBtn) {
    elements.leaveLobbyBtn.onclick = () => {
      if (isWsReady() && state.currentLobby?.lobby_id) {
        state.ws?.send(
          JSON.stringify({
            type: "lobby_leave",
            lobby_id: state.currentLobby.lobby_id,
          }),
        );
      }
      state.currentLobby = null;
      renderAuthState();
      renderCurrentLobby();
      renderLobbyList();
    };
  }
}
