const lobbyId = window.location.pathname.split("/").pop();
const statusEl = document.getElementById("game-status");
const eventsEl = document.getElementById("game-events");
const choicesEl = document.getElementById("game-choices");
const boardEl = document.getElementById("board");

let myPlayerId = null;
let lastState = null;
let boardSnapshot = null;
const tileMap = new Map();

const playerColors = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8",
    "#f58231", "#911eb4", "#46f0f0", "#f032e6",
]

function positionToGrid(pos) {
    if (pos === 0) return { col: 10, row: 10 };
    if (pos >= 1 && pos <= 9) return { col: 10 - pos, row: 10 };
    if (pos === 10) return { col: 0, row: 10 };
    if (pos >= 11 && pos <= 19) return { col: 0, row: 20 - pos };
    if (pos === 20) return { col: 0, row: 0 };
    if (pos >= 21 && pos <= 29) return { col: pos - 20, row: 0 };
    if (pos === 30) return { col: 10, row: 0 };
    return { col: 10, row: pos - 30 };
}

function formatName(name) {
    return name.replace(/_/g, " ").toUpperCase();
}

function renderBoard(board) {
    boardSnapshot = board;

    document.querySelectorAll(".board-tile").forEach((el) => el.remove());
    tileMap.clear();

    boardSnapshot.forEach((tile) => {
        const pos = tile.position;
        const coords = positionToGrid(pos);

        const tileEl = document.createElement("div");
        tileEl.className = "board-tile";
        tileEl.style.gridColumn = String(coords.col + 1);
        tileEl.style.gridRow = String(coords.row + 1);
        tileEl.dataset.position = String(pos);

        const nameEl = document.createElement("div");
        nameEl.className = "tile-name";
        nameEl.textContent = formatName(tile.name);

        const playersEl = document.createElement("div");
        playersEl.className = "tile-players";

        tileEl.append(nameEl, playersEl);
        boardEl.appendChild(tileEl);
        tileMap.set(pos, tileEl);
    });

    if (lastState) {
        updatePlayers(lastState);
    }
}

function updatePlayers(state) {
    tileMap.forEach((tileEl) => {
        const playersEl = tileEl.querySelector(".tile-players");
        playersEl.textContent = "";
    });

    state.players.forEach((p) => {
        const tileEl = tileMap.get(p.position);
        if (!tileEl) return;

        const dot = document.createElement("span");
        dot.className = "player-dot";
        dot.title = `P${p.id}`;
        dot.style.backgroundColor = playerColors[p.id % playerColors.length];

        tileEl.querySelector(".tile-players").appendChild(dot);
    });
}

function renderState(state) {
    lastState = state;
    statusEl.textContent = `Turn: ${state.current_player_id} | Phase: ${state.turn_phase}`;
    updatePlayers(state);
}

function renderEvents(events) {
    events.forEach((e) => {
        const row = document.createElement("div");
        row.textContent = `${e.type}: ${JSON.stringify(e)}`;
        eventsEl.appendChild(row);
    });
    eventsEl.scrollTop = eventsEl.scrollHeight;
}

function choiceLabel(choice) {
    const entries = Object.entries(choice).filter(([k]) => k !== "type");
    const short = entries.slice(0, 2).map(([k, v]) => `${k}=${v}`).join(", ");
    return `${choice.type}${short ? " (" + short + ")" : ""}`;
}

function renderChoices(choices) {
    choicesEl.textContent = "";
    choices.forEach((choice) => {
        const btn = document.createElement("button");
        btn.textContent = choiceLabel(choice);
        btn.addEventListener("click", () => {
            ws.send(JSON.stringify({ type: "choice", choice }));
        });
        choicesEl.appendChild(btn);
    });
}

const wsProto = location.protocol === "https:" ? "wss" : "ws";
const ws = new WebSocket(`${wsProto}://${location.host}/ws/games/${lobbyId}`);

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "init") {
        myPlayerId = msg.player_id;
        renderBoard(msg.board);
        renderState(msg.state);
        renderChoices(msg.choices);
    }

    if (msg.type === "state") {
        renderEvents(msg.events || []);
        renderState(msg.state);
    }

    if (msg.type === "choices") {
        renderChoices(msg.choices);
    }

    if (msg.type === "board") {
        renderBoard(msg.board);
    }
};

ws.onclose = (event) => {
    if (event.code === 1008) {
        window.location.href = "/login";
    }
};