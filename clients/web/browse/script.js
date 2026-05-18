const lobbyList = document.getElementById("lobby-list");
const createButton = document.getElementById("create-lobby");

async function loadLobbies() {
    const response = await fetch("/lobbies", {
        method: "GET",
        credentials: "include"
    });
    if (!response.ok) {
        lobbyList.textContent = "Failed to load lobbies.";
        return;
    }

    const lobbies = await response.json();
    lobbyList.textContent = "";

    if (lobbies.length === 0) {
        lobbyList.textContent = "No lobbies available.";
        return;
    }

    lobbies.forEach((lobby) => {
        const row = document.createElement("div");
        row.className = "lobby-row";

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

        const joinButton = document.createElement("button");
        joinButton.textContent = "Join";
        joinButton.addEventListener("click", () => joinLobby(lobby.lobby_id));
        joinButton.dataset.id = lobby.lobby_id;

        row.append(playersEl, joinButton);
        lobbyList.appendChild(row);
    });
}


async function joinLobby(lobbyId) {
    const response = await fetch(`/lobbies/${lobbyId}/join`, {
        method: "POST",
        credentials: "include"
    });

    if (!response.ok) {
        alert("Failed to join lobby.");
        return;
    }

    alert("Joined lobby" + lobbyId);
}


createButton.addEventListener("click", async () => {
    const response = await fetch("/lobbies/create", {
        method: "POST",
        credentials: "include"
    });
    if (!response.ok) {
        alert("Failed to create lobby.");
        return;
    }

    const lobby = await response.json();
    alert("Created lobby " + lobby.lobby_id);
    loadLobbies();
});

loadLobbies();
setInterval(loadLobbies, 2000);