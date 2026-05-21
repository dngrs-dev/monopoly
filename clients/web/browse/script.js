// Lobbies list management and UI rendering
const lobbyList = document.getElementById("lobby-list");
const lobbies = new Map();

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
            img.src = player.avatar_url;
            img.alt = player.display_name;

            const name = document.createElement("span");
            name.textContent = player.display_name;

            playerEl.append(img, name);
            playersEl.appendChild(playerEl);
        });
        row.append(meta, playersEl);

        if (lobby.players.length < lobby.max_players) {
            const joinButton = document.createElement("button");
            joinButton.textContent = "Join";
            joinButton.addEventListener("click", () => joinLobby(lobby.lobby_id));
            row.append(joinButton);
        }

        if (lobby.players.length > 0) {
            if (lobby.host_id === lobby.players[0].player_id) { // If the host not the first player, this should be changed
                const deleteButton = document.createElement("button");
                deleteButton.textContent = "Delete";
                deleteButton.addEventListener("click", () => deleteLobby());
                row.append(deleteButton);
            }
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
    renderAll();
}

function addPlayer(lobbyId, player) {
    const lobby = lobbies.get(lobbyId);
    if (!lobby) return;
    if (!lobby.players.find((p) => p.player_id === player.player_id)) {
        lobby.players.push(player);
    }
    renderAll();
}

function removePlayer(lobbyId, playerId) {
    const lobby = lobbies.get(lobbyId);
    if (!lobby) return;
    lobby.players = lobby.players.filter((p) => p.player_id !== playerId);
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
}

async function deleteLobby() {
    const response = await fetch(`/lobbies/delete`, {
        method: "POST",
        credentials: "include"
    });
}

// Websocket setup (lobbies updates)
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
};

ws.onclose = (event) => {
    console.log("WebSocket closed:", event);
    if (event.code === 1006) {
        window.location.href = "/login";
    }
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