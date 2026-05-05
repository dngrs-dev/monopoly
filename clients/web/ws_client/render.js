import { elements, state, setError, isWsReady } from "./context.js";
import { formatCountdown } from "./utils.js";

export function updateOwnerCountdown() {
  if (!elements.ownerCountdownRow || !elements.ownerCountdownEl) return;
  const isOwner =
    state.currentLobby &&
    state.currentUser &&
    state.currentLobby.owner_user_id === state.currentUser.user_id;

  if (!isOwner || !Number.isFinite(state.countdownExpiresAt)) {
    elements.ownerCountdownRow.hidden = true;
    elements.ownerCountdownEl.textContent = "--:--";
    return;
  }

  elements.ownerCountdownRow.hidden = false;
  const secondsLeft = (state.countdownExpiresAt - Date.now()) / 1000;
  elements.ownerCountdownEl.textContent = formatCountdown(secondsLeft);
}

export function renderAuthState() {
  const canUseLobby = state.authed && isWsReady();

  if (elements.createLobbyBtn)
    elements.createLobbyBtn.disabled = !canUseLobby || !!state.currentLobby;
  if (elements.joinPrivateBtn)
    elements.joinPrivateBtn.disabled = !canUseLobby || !!state.currentLobby;
  if (elements.logoutBtn) elements.logoutBtn.disabled = !state.authed;
  if (elements.profileBtn) elements.profileBtn.disabled = !state.authed;
  if (elements.currentUserEl)
    elements.currentUserEl.textContent =
      state.currentUser?.username || "(not signed in)";
}

export function renderLobbyList() {
  if (!elements.lobbyListEl) return;

  elements.lobbyListEl.innerHTML = "";

  if (!state.authed) {
    elements.lobbyListEl.textContent = "(sign in to see lobbies)";
    return;
  }

  if (!isWsReady()) {
    elements.lobbyListEl.textContent = "(connecting...)";
    return;
  }

  if (!Array.isArray(state.lobbyList) || state.lobbyList.length === 0) {
    elements.lobbyListEl.textContent = "(no public lobbies)";
    return;
  }

  for (const lobby of state.lobbyList) {
    const members = Array.isArray(lobby?.members) ? lobby.members : [];
    const memberNames = members
      .map((member) => member?.username || member?.user_id)
      .filter(Boolean)
      .join(", ");
    const limit = Number.isInteger(lobby?.user_limit) ? lobby.user_limit : null;
    const isFull = limit !== null && members.length >= limit;

    const li = document.createElement("li");

    const title = document.createElement("div");
    const limitText = limit === null ? "?" : String(limit);
    title.textContent = `Lobby ${lobby?.lobby_id || "?"} (${members.length}/${limitText})`;

    const owner = document.createElement("div");
    owner.textContent = `Owner: ${
      lobby?.owner_username || lobby?.owner_user_id || "(unknown)"
    }`;

    const players = document.createElement("div");
    players.textContent = `Players: ${memberNames || "(none)"}`;

    const joinBtn = document.createElement("button");
    joinBtn.textContent = "Join";
    joinBtn.disabled =
      !isWsReady() || !!state.currentLobby || lobby?.started || isFull;
    joinBtn.onclick = () => {
      if (!isWsReady() || !state.ws) return;
      if (!lobby?.lobby_id) return;
      setError("");
      state.ws.send(JSON.stringify({ type: "lobby_join", lobby_id: lobby.lobby_id }));
    };

    li.appendChild(title);
    li.appendChild(owner);
    li.appendChild(players);
    li.appendChild(joinBtn);
    elements.lobbyListEl.appendChild(li);
  }
}

export function renderCurrentLobby() {
  if (!elements.myLobbySection) return;

  if (!state.currentLobby) {
    elements.myLobbySection.hidden = true;
    if (elements.myLobbyIdEl) elements.myLobbyIdEl.textContent = "(none)";
    if (elements.myLobbyOwnerEl) elements.myLobbyOwnerEl.textContent = "(none)";
    if (elements.myLobbyVisibilityEl)
      elements.myLobbyVisibilityEl.textContent = "(none)";
    if (elements.myLobbyInviteEl) elements.myLobbyInviteEl.textContent = "(none)";
    if (elements.myLobbyLimitEl) elements.myLobbyLimitEl.textContent = "(none)";
    if (elements.myLobbyMembersEl) elements.myLobbyMembersEl.textContent = "(none)";
    state.countdownExpiresAt = null;
    updateOwnerCountdown();
    return;
  }

  elements.myLobbySection.hidden = false;

  const members = Array.isArray(state.currentLobby.members)
    ? state.currentLobby.members
    : [];
  const memberNames = members
    .map((member) => member?.username || member?.user_id)
    .filter(Boolean)
    .join(", ");
  const limit = Number.isInteger(state.currentLobby.user_limit)
    ? state.currentLobby.user_limit
    : null;

  if (elements.myLobbyIdEl)
    elements.myLobbyIdEl.textContent = state.currentLobby.lobby_id || "(none)";
  if (elements.myLobbyOwnerEl)
    elements.myLobbyOwnerEl.textContent =
      state.currentLobby.owner_username ||
      state.currentLobby.owner_user_id ||
      "(unknown)";
  if (elements.myLobbyVisibilityEl)
    elements.myLobbyVisibilityEl.textContent = state.currentLobby.is_public
      ? "public"
      : "private";
  if (elements.myLobbyInviteEl) {
    elements.myLobbyInviteEl.textContent = state.currentLobby.is_public
      ? "(public lobby)"
      : state.currentLobby.invite_code || "(pending)";
  }
  if (elements.myLobbyLimitEl)
    elements.myLobbyLimitEl.textContent =
      limit === null ? "?" : `${members.length}/${limit}`;
  if (elements.myLobbyMembersEl)
    elements.myLobbyMembersEl.textContent = memberNames || "(none)";

  if (Number.isFinite(state.currentLobby.idle_expires_at)) {
    state.countdownExpiresAt = state.currentLobby.idle_expires_at * 1000;
  } else {
    state.countdownExpiresAt = null;
  }

  const isOwner =
    state.currentUser &&
    state.currentLobby.owner_user_id === state.currentUser.user_id;
  if (elements.startLobbyBtn)
    elements.startLobbyBtn.disabled =
      !(isOwner && isWsReady() && !state.currentLobby.started);
  if (elements.leaveLobbyBtn)
    elements.leaveLobbyBtn.disabled = !isWsReady();
  updateOwnerCountdown();
}
