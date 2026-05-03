const createLobbyBtn = document.getElementById("create-lobby");
const lobbyLimitInput = document.getElementById("lobby-limit");
const lobbyVisibilitySelect = document.getElementById("lobby-visibility");
const lobbyListEl = document.getElementById("lobby-list");
const myLobbySection = document.getElementById("my-lobby");
const myLobbyIdEl = document.getElementById("my-lobby-id");
const myLobbyOwnerEl = document.getElementById("my-lobby-owner");
const myLobbyVisibilityEl = document.getElementById("my-lobby-visibility");
const myLobbyLimitEl = document.getElementById("my-lobby-limit");
const myLobbyMembersEl = document.getElementById("my-lobby-members");
const startLobbyBtn = document.getElementById("start-lobby");
const leaveLobbyBtn = document.getElementById("leave-lobby");
const statusEl = document.getElementById("ws-status");
const loginBtn = document.getElementById("login");
const logoutBtn = document.getElementById("logout");
const changeUsernameBtn = document.getElementById("change-username");
const currentUserEl = document.getElementById("current-user");
const errEl = document.getElementById("err");

let ws = null;
let lobbyList = [];
let currentLobby = null;
let authed = false;
let currentUser = null;

function setError(text) {
  if (errEl) errEl.textContent = text || "";
}

function setStatus(text) {
  if (statusEl) statusEl.textContent = text || "";
}

function isWsReady() {
  return ws && ws.readyState === WebSocket.OPEN;
}

function clampLobbyLimit(value) {
  if (!Number.isFinite(value)) return 4;
  if (value < 1) return 1;
  if (value > 8) return 8;
  return value;
}

function renderAuthState() {
  const canUseLobby = authed && isWsReady();

  if (createLobbyBtn)
    createLobbyBtn.disabled = !canUseLobby || !!currentLobby;
  if (logoutBtn) logoutBtn.disabled = !authed;
  if (changeUsernameBtn) changeUsernameBtn.disabled = !authed;
  if (currentUserEl)
    currentUserEl.textContent = currentUser?.username || "(not signed in)";
}

function renderLobbyList() {
  if (!lobbyListEl) return;

  lobbyListEl.innerHTML = "";

  if (!authed) {
    lobbyListEl.textContent = "(sign in to see lobbies)";
    return;
  }

  if (!isWsReady()) {
    lobbyListEl.textContent = "(connecting...)";
    return;
  }

  if (!Array.isArray(lobbyList) || lobbyList.length === 0) {
    lobbyListEl.textContent = "(no public lobbies)";
    return;
  }

  for (const lobby of lobbyList) {
    const members = Array.isArray(lobby?.members) ? lobby.members : [];
    const memberNames = members
      .map((member) => member?.username || member?.user_id)
      .filter(Boolean)
      .join(", ");
    const limit = Number.isInteger(lobby?.user_limit)
      ? lobby.user_limit
      : null;
    const isFull = limit !== null && members.length >= limit;

    const li = document.createElement("li");

    const title = document.createElement("div");
    const limitText = limit === null ? "?" : String(limit);
    title.textContent = `Lobby ${lobby?.lobby_id || "?"} (${members.length}/${
      limitText
    })`;

    const owner = document.createElement("div");
    owner.textContent = `Owner: ${
      lobby?.owner_username || lobby?.owner_user_id || "(unknown)"
    }`;

    const players = document.createElement("div");
    players.textContent = `Players: ${memberNames || "(none)"}`;

    const joinBtn = document.createElement("button");
    joinBtn.textContent = "Join";
    joinBtn.disabled =
      !isWsReady() || !!currentLobby || lobby?.started || isFull;
    joinBtn.onclick = () => {
      if (!isWsReady()) return;
      if (!lobby?.lobby_id) return;
      setError("");
      ws.send(JSON.stringify({ type: "lobby_join", lobby_id: lobby.lobby_id }));
    };

    li.appendChild(title);
    li.appendChild(owner);
    li.appendChild(players);
    li.appendChild(joinBtn);
    lobbyListEl.appendChild(li);
  }
}

function renderCurrentLobby() {
  if (!myLobbySection) return;

  if (!currentLobby) {
    myLobbySection.hidden = true;
    if (myLobbyIdEl) myLobbyIdEl.textContent = "(none)";
    if (myLobbyOwnerEl) myLobbyOwnerEl.textContent = "(none)";
    if (myLobbyVisibilityEl) myLobbyVisibilityEl.textContent = "(none)";
    if (myLobbyLimitEl) myLobbyLimitEl.textContent = "(none)";
    if (myLobbyMembersEl) myLobbyMembersEl.textContent = "(none)";
    return;
  }

  myLobbySection.hidden = false;

  const members = Array.isArray(currentLobby.members)
    ? currentLobby.members
    : [];
  const memberNames = members
    .map((member) => member?.username || member?.user_id)
    .filter(Boolean)
    .join(", ");
  const limit = Number.isInteger(currentLobby.user_limit)
    ? currentLobby.user_limit
    : null;

  if (myLobbyIdEl) myLobbyIdEl.textContent = currentLobby.lobby_id || "(none)";
  if (myLobbyOwnerEl)
    myLobbyOwnerEl.textContent =
      currentLobby.owner_username || currentLobby.owner_user_id || "(unknown)";
  if (myLobbyVisibilityEl)
    myLobbyVisibilityEl.textContent = currentLobby.is_public
      ? "public"
      : "private";
  if (myLobbyLimitEl)
    myLobbyLimitEl.textContent =
      limit === null ? "?" : `${members.length}/${limit}`;
  if (myLobbyMembersEl)
    myLobbyMembersEl.textContent = memberNames || "(none)";

  const isOwner =
    currentUser && currentLobby.owner_user_id === currentUser.user_id;
  if (startLobbyBtn)
    startLobbyBtn.disabled = !(isOwner && isWsReady() && !currentLobby.started);
  if (leaveLobbyBtn) leaveLobbyBtn.disabled = !isWsReady();
}

async function checkAuth() {
  setError("");
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (!res.ok) {
      authed = false;
      currentUser = null;
      renderAuthState();
      renderLobbyList();
      renderCurrentLobby();
      disconnectWs();
      return;
    }

    currentUser = await res.json().catch(() => null);
    authed = !!currentUser;
  } catch {
    authed = false;
    currentUser = null;
  }

  renderAuthState();
  renderLobbyList();
  renderCurrentLobby();
  if (authed) connectWs();
}

function disconnectWs() {
  if (ws) {
    try {
      ws.close();
    } catch {}
  }
  ws = null;
  setStatus("disconnected");
}

function connectWs() {
  if (!authed) return;
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const url = new URL(window.location.href);
  const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProto}//${url.host}/ws`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    setStatus("connected");
    setError("");
    renderAuthState();
    renderLobbyList();
    renderCurrentLobby();
    ws.send(JSON.stringify({ type: "lobby_list" }));
  };

  ws.onmessage = (evt) => {
    try {
      handleMessage(JSON.parse(evt.data));
    } catch {
      setError("Bad JSON from server");
    }
  };

  ws.onclose = () => {
    setStatus("disconnected");
    renderAuthState();
    renderLobbyList();
    renderCurrentLobby();
  };

  ws.onerror = () => {
    setError("WebSocket error");
  };
}

function handleMessage(data) {
  if (!data) return;

  if (data.type === "error") {
    setError(data.message || "Unknown error");
    return;
  }

  if (data.type === "lobby_list") {
    lobbyList = Array.isArray(data.lobbies) ? data.lobbies : [];
    renderLobbyList();
    return;
  }

  if (data.type === "lobby_joined") {
    currentLobby = data.lobby || null;
    renderAuthState();
    renderCurrentLobby();
    renderLobbyList();
    return;
  }

  if (data.type === "lobby_update") {
    if (currentLobby && data.lobby?.lobby_id === currentLobby.lobby_id) {
      currentLobby = data.lobby;
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
    currentLobby = null;
    setError(data.message || "Lobby closed");
    renderAuthState();
    renderCurrentLobby();
    renderLobbyList();
  }
}

loginBtn.onclick = () => {
  window.location.href = "/login";
};

logoutBtn.onclick = async () => {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
    });
  } catch {}

  setError("");
  authed = false;
  currentUser = null;
  lobbyList = [];
  currentLobby = null;
  disconnectWs();
  renderAuthState();
  renderLobbyList();
  renderCurrentLobby();
};

changeUsernameBtn.onclick = async () => {
  setError("");
  await checkAuth();
  if (!authed || !currentUser) return;

  const next = window.prompt(
    "Choose a new username (1-32 chars)",
    currentUser.username,
  );
  if (next === null) return;

  const username = next.trim();
  if (!username) {
    setError("Username is required");
    return;
  }

  const res = await fetch("/api/auth/username", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ username }),
  });

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    setError(data?.detail || "Could not update username");
    return;
  }

  currentUser = data?.user || currentUser;
  renderAuthState();
  renderCurrentLobby();
  renderLobbyList();
};

if (createLobbyBtn) {
  createLobbyBtn.onclick = async () => {
    setError("");
    await checkAuth();
    if (!authed || !isWsReady() || currentLobby) return;

    const raw = parseInt(lobbyLimitInput?.value ?? "", 10);
    const limit = clampLobbyLimit(raw);
    const visibility = lobbyVisibilitySelect?.value || "public";
    const isPublic = visibility !== "private";

    ws.send(
      JSON.stringify({
        type: "lobby_create",
        user_limit: limit,
        is_public: isPublic,
      }),
    );
  };
}

if (startLobbyBtn) {
  startLobbyBtn.onclick = () => {
    if (!isWsReady() || !currentLobby?.lobby_id) return;
    ws.send(
      JSON.stringify({
        type: "lobby_start",
        lobby_id: currentLobby.lobby_id,
      }),
    );
  };
}

if (leaveLobbyBtn) {
  leaveLobbyBtn.onclick = () => {
    if (isWsReady() && currentLobby?.lobby_id) {
      ws.send(
        JSON.stringify({
          type: "lobby_leave",
          lobby_id: currentLobby.lobby_id,
        }),
      );
    }
    currentLobby = null;
    renderAuthState();
    renderCurrentLobby();
    renderLobbyList();
  };
}

checkAuth();
