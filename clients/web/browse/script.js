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
        row.innerHTML = `
            <div class="lobby-id">Id: ${lobby.lobby_id}</div>
            <div class="lobby-players">Players: ${lobby.players.length} / ${lobby.max_players}</div>
            <button data-id="${lobby.lobby_id}">Join</button>
        `;
        row.querySelector("button").addEventListener("click", () => joinLobby(lobby.lobby_id));
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