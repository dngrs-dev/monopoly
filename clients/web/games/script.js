const lobbyId = window.location.pathname.split("/").pop();
const statusEl = document.getElementById("game-status");
const playersEl = document.getElementById("game-players");
const eventsEl = document.getElementById("game-events");
const choicesEl = document.getElementById("game-choices");

let myPlayerId = null;
let lastState = null;

function renderState(state) {
    lastState = state;
    statusEl.textContent = `Turn: ${state.current_player_id} | Phase: ${state.turn_phase}`;

    playersEl.textContent = "";
    state.players.forEach((p) => {
        const row = document.createElement("div");
        row.textContent = `P${p.id} | $${p.balance} | pos ${p.position}` +
            (p.in_jail ? " | in jail" : "") +
            (p.bankrupt ? " | bankrupt" : "") +
            (p.id === myPlayerId ? " | YOU" : "") +
            (p.id === state.current_player_id ? " | CURRENT" : "");
        playersEl.appendChild(row);
    });
}

function renderEvents(events) {
    events.forEach((e) => {
        const row = document.createElement("div");
        row.textContent = `${e.type}: ${JSON.stringify(e)}`;
        eventsEl.appendChild(row);
    });
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
};

ws.onclose = (event) => {
    if (event.code === 1008) {
        window.location.href = "/login";
    }
};