// Lobbies list management and UI rendering
const lobbyList = document.getElementById("lobby-list");
const lobbies = new Map();
let currentUserId = null;
let currentLobbyId = null;
let ws = null;

async function loadCurrentUser() {
    const response = await fetch("/auth/session", {
        method: "GET",
        credentials: "include"
    });
    if (!response.ok) {
        window.location.href = "/login";
        return;
    }
    const user = await response.json();
    currentUserId = user.id;
}

async function loadCurrentLobby() {
    const response = await fetch("/lobbies/me", {
        method: "GET",
        credentials: "include"
    });
    if (response.ok) {
        const lobby = await response.json();
        currentLobbyId = lobby ? lobby.lobby_id : null;
    } else {
        currentLobbyId = null;
    }
}

function isUserInLobby(lobby) {
    return currentUserId && lobby.players.some((p) => p.id === currentUserId);
}

function renderAll() {
    lobbyList.textContent = "";
    if (lobbies.size === 0) {
        lobbyList.textContent = "No lobbies available.";
        return;
    }

    for (const lobby of lobbies.values()) {
        const row = document.createElement("div");
        row.className = "lobby-row";

        const meta = document.createElement("div");
        meta.className = "lobby-meta";
        meta.textContent = `${lobby.players.length}/${lobby.max_players}  ${lobby.lobby_id}`;

        const playersEl = document.createElement("div");
        playersEl.className = "lobby-players";

        lobby.players.forEach((player) => {
            const playerEl = document.createElement("div");
            playerEl.className = "lobby-player";

            const img = document.createElement("img");
            img.className = "avatar avatar--sm";
            img.src = player.avatar_url;
            img.alt = player.display_name;

            const name = document.createElement("span");
            name.textContent = player.display_name;

            playerEl.append(img, name);
            playersEl.appendChild(playerEl);
        });
        row.append(meta, playersEl);

        const userInLobby = isUserInLobby(lobby);
        const isHost = currentUserId && lobby.host_id === currentUserId;

        if (!currentLobbyId && !lobby.started && lobby.players.length < lobby.max_players && !userInLobby) {
            const joinButton = document.createElement("button");
            joinButton.textContent = "Join";
            joinButton.addEventListener("click", () => joinLobby(lobby.lobby_id));
            row.append(joinButton);
        }

        if (userInLobby && !isHost) {
            const leaveButton = document.createElement("button");
            leaveButton.textContent = "Leave";
            leaveButton.addEventListener("click", () => leaveLobby());
            row.append(leaveButton);
        }

        if (isHost) {
            const startButton = document.createElement("button");
            startButton.textContent = "Start";
            startButton.addEventListener("click", () => startGame(lobby.lobby_id));
            row.append(startButton);

            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Delete";
            deleteButton.addEventListener("click", () => deleteLobby());
            row.append(deleteButton);
        }

        lobbyList.appendChild(row);
    }
}

function upsertLobby(lobby) {
    lobbies.set(lobby.lobby_id, lobby);
    renderAll();
}

function removeLobby(lobbyId) {
    lobbies.delete(lobbyId);
    if (currentLobbyId === lobbyId) {
        currentLobbyId = null;
    }
    renderAll();
}

function addPlayer(lobbyId, player) {
    const lobby = lobbies.get(lobbyId);
    if (!lobby) return;
    if (!lobby.players.find((p) => p.id === player.player_id)) {
        lobby.players.push(player);
    }
    if (player.id === currentUserId) {
        currentLobbyId = lobbyId;
    }
    renderAll();
}

function removePlayer(lobbyId, playerId) {
    const lobby = lobbies.get(lobbyId);
    if (!lobby) return;
    lobby.players = lobby.players.filter((p) => p.id !== playerId);
    if (playerId === currentUserId && currentLobbyId === lobbyId) {
        currentLobbyId = null;
    }
    renderAll();
}

function setHost(lobbyId, hostId) {
    const lobby = lobbies.get(lobbyId);
    if (!lobby) return;
    lobby.host_id = hostId;
    renderAll();
}

async function joinLobby(lobbyId) {
    const response = await fetch(`/lobbies/join/${lobbyId}`, {
        method: "POST",
        credentials: "include"
    });
    if (response.ok) {
        const lobby = await response.json();
        currentLobbyId = lobby.lobby_id;
    }
}

async function leaveLobby() {
    const response = await fetch(`/lobbies/leave`, {
        method: "POST",
        credentials: "include"
    });
    if (response.ok) {
        currentLobbyId = null;
    }
}

async function startGame(lobbyId) {
    const response = await fetch(`/lobbies/start/${lobbyId}`, {
        method: "POST",
        credentials: "include"
    });
    if (response.ok) {
        window.location.href = `/games/${lobbyId}`;
    }
}

async function deleteLobby() {
    const response = await fetch(`/lobbies/delete`, {
        method: "POST",
        credentials: "include"
    });
}


// Create lobby modal
const createButton = document.getElementById("create-lobby");
const modal = document.getElementById("create-lobby-modal");
const confirmButton = document.getElementById("create-lobby-confirm");
const cancelButton = document.getElementById("create-lobby-cancel");
const maxPlayersInput = document.getElementById("lobby-max-players");

createButton.addEventListener("click", () => {
    modal.hidden = false;
});

cancelButton.addEventListener("click", () => {
    modal.hidden = true;
});

confirmButton.addEventListener("click", async () => {
    const maxPlayers = Number(maxPlayersInput.value);

    const response = await fetch("/lobbies/create", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_players: maxPlayers })
    });

    if (!response.ok) {
        alert("Failed to create lobby");
        return;
    }

    modal.hidden = true;

});



async function init() {
    await loadCurrentUser();
    await loadCurrentLobby();
    connectWebSocket();
}

// Websocket setup (lobbies updates)
function connectWebSocket() {
    const wsProto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${wsProto}://${location.host}/ws/lobbies`);

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "init") {
            lobbies.clear();
            msg.lobbies.forEach((lobby) => lobbies.set(lobby.lobby_id, lobby));
            renderAll();
        }

        if (msg.type === "create") {
            upsertLobby(msg.lobby);
        }

        if (msg.type === "join") {
            addPlayer(msg.lobby_id, msg.player);
        }

        if (msg.type === "leave") {
            removePlayer(msg.lobby_id, msg.player_id);
        }

        if (msg.type === "remove") {
            removeLobby(msg.lobby_id);
        }

        if (msg.type === "host") {
            setHost(msg.lobby_id, msg.host_id);
        }

        if (msg.type === "started") {
            const lobby = msg.lobby;
            lobbies.set(lobby.lobby_id, lobby);
            if (lobby.players.some((p) => p.id === currentUserId)) {
                currentLobbyId = lobby.lobby_id;
                window.location.href = `/games/${lobby.lobby_id}`;
            }

            renderAll();
        }
    };

    ws.onclose = (event) => {
        console.log("WebSocket closed:", event);
        if (event.code === 1006) {
            window.location.href = "/login";
        }
    };
}

init();