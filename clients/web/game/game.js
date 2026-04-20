let ws = null;
let lastSnapshot = null;
let lastSendTradeChoice = null;
let myPlayerId = null;

const $ = (id) => document.getElementById(id);

function setStatus(text) {
  const el = $("status");
  if (el) el.textContent = text;
}

function setError(text) {
  const el = $("err");
  if (el) el.textContent = text || "";
}

function renderJson(el, obj) {
  if (!el) return;
  el.textContent = obj ? JSON.stringify(obj, null, 2) : "(none)";
}

function setMeDisplay(username) {
  const el = $("me");
  if (el) el.textContent = username || "(unknown)";
}

function setPlayerDisplay(value) {
  const el = $("player");
  if (!el) return;
  el.textContent = value == null ? "(spectator)" : String(value);
}

function getRoomFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const room = (params.get("room") || "").trim();
  return room || "room1";
}

async function fetchMe() {
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (res.status === 401) return null;
    if (!res.ok) return null;
    return await res.json(); // { user_id, username }
  } catch {
    return null;
  }
}

function isMyChoice(choice) {
  if (!choice) return false;
  if (!Number.isInteger(myPlayerId)) return false;
  return choice.player_id === myPlayerId;
}

function renderTradePanel(sendChoice) {
  const offeredRoot = $("trade_offered_props");
  const requestedRoot = $("trade_requested_props");

  if (offeredRoot) offeredRoot.innerHTML = "";
  if (requestedRoot) requestedRoot.innerHTML = "";
  if (!offeredRoot || !requestedRoot) return;

  if (!lastSnapshot || !sendChoice) {
    offeredRoot.textContent = "(none)";
    requestedRoot.textContent = "(none)";
    return;
  }

  const tiles = Array.isArray(lastSnapshot.tiles) ? lastSnapshot.tiles : [];
  const offered = [];
  const requested = [];

  for (let pos = 0; pos < tiles.length; pos++) {
    const t = tiles[pos];
    if (!t || typeof t !== "object") continue;
    if (!("owner" in t)) continue; // Ownable tiles have `owner`

    if (t.owner === sendChoice.player_id) offered.push({ pos, name: t.name });
    if (t.owner === sendChoice.receiving_player_id)
      requested.push({ pos, name: t.name });
  }

  if (offered.length === 0) offeredRoot.textContent = "(none)";
  for (const it of offered) {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.name = "trade_offered_pos";
    cb.value = String(it.pos);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(` ${it.name} (#${it.pos})`));
    offeredRoot.appendChild(label);
    offeredRoot.appendChild(document.createElement("div"));
  }

  if (requested.length === 0) requestedRoot.textContent = "(none)";
  for (const it of requested) {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.name = "trade_requested_pos";
    cb.value = String(it.pos);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(` ${it.name} (#${it.pos})`));
    requestedRoot.appendChild(label);
    requestedRoot.appendChild(document.createElement("div"));
  }
}

function renderChoices(choiceList) {
  const root = $("choices");
  if (!root) return;

  root.innerHTML = "";

  lastSendTradeChoice = null;
  if (Array.isArray(choiceList) && Number.isInteger(myPlayerId)) {
    for (const item of choiceList) {
      const c = item?.choice;
      if (c?.type === "SendTradeOfferChoice" && c.player_id === myPlayerId) {
        lastSendTradeChoice = c;
        break;
      }
    }
  }
  renderTradePanel(lastSendTradeChoice);

  if (!Array.isArray(choiceList) || choiceList.length === 0) {
    root.textContent = "(none)";
    return;
  }

  for (const item of choiceList) {
    const c = item?.choice;
    const mine = isMyChoice(c);

    const btn = document.createElement("button");
    btn.textContent = `${c?.type || "Choice"} (${String(item?.id || "").slice(0, 8)})`;
    btn.disabled = !mine || !ws || ws.readyState !== WebSocket.OPEN;

    btn.onclick = () => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      if (!mine) return;

      const room = $("room")?.value || "room1";
      let payload = undefined;

      if (c?.type === "SendTradeOfferChoice") {
        const offered_money =
          parseInt($("trade_offered_money")?.value ?? "0", 10) || 0;
        const requested_money =
          parseInt($("trade_requested_money")?.value ?? "0", 10) || 0;

        const offered_positions = Array.from(
          document.querySelectorAll('input[name="trade_offered_pos"]:checked'),
        ).map((x) => parseInt(x.value, 10));

        const requested_positions = Array.from(
          document.querySelectorAll(
            'input[name="trade_requested_pos"]:checked',
          ),
        ).map((x) => parseInt(x.value, 10));

        payload = {
          offered_money,
          requested_money,
          offered_properties_positions: offered_positions,
          requested_properties_positions: requested_positions,
        };
      }

      const msg = {
        type: "choose",
        room_id: room,
        choice_id: item.id,
      };
      if (payload !== undefined) msg.payload = payload;

      ws.send(JSON.stringify(msg));
    };

    const details = document.createElement("span");
    details.style.marginLeft = "6px";
    details.style.fontSize = "12px";
    details.textContent = JSON.stringify(c);

    const line = document.createElement("div");
    line.appendChild(btn);
    line.appendChild(details);
    root.appendChild(line);
  }
}

function onMessage(data) {
  setError("");

  if (data?.type === "error") {
    setError(data.message);
    return;
  }

  if (data?.type === "joined") {
    myPlayerId = data.you?.player_id ?? null;
    setPlayerDisplay(myPlayerId);

    lastSnapshot = data.snapshot ?? null;
    renderJson($("snapshot"), lastSnapshot);
    renderJson($("events"), null);
    renderChoices(data.choices);
    return;
  }

  if (data?.type === "update") {
    lastSnapshot = data.snapshot ?? null;
    renderJson($("snapshot"), lastSnapshot);
    renderJson($("events"), data.events ?? null);
    renderChoices(data.choices);
    return;
  }
}

function connectWs(room) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.close();

  const url = new URL(window.location.href);
  const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProto}//${url.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    setStatus("connected");
    const disc = $("disconnect");
    if (disc) disc.disabled = false;

    myPlayerId = null;
    setPlayerDisplay(null);

    ws.send(JSON.stringify({ type: "join", room_id: room }));
  };

  ws.onmessage = (evt) => {
    try {
      onMessage(JSON.parse(evt.data));
    } catch {
      setError("Bad JSON from server");
    }
  };

  ws.onclose = (evt) => {
    setStatus("disconnected");
    const disc = $("disconnect");
    if (disc) disc.disabled = true;

    if (evt?.code === 1008) {
      setError("Not authenticated. Go to main page and click Login.");
    }
  };

  ws.onerror = () => {
    setError("WebSocket error");
  };
}

const disconnectBtn = $("disconnect");
if (disconnectBtn) {
  disconnectBtn.onclick = () => {
    try {
      if (ws) ws.close();
    } catch {}
    window.location.href = "/";
  };
}

(async function start() {
  setStatus("disconnected");

  const room = getRoomFromUrl();
  const roomInput = $("room");
  if (roomInput) {
    roomInput.value = room;
    roomInput.disabled = true; // no Connect button here, so don’t let it mislead
  }

  const me = await fetchMe();
  if (!me) {
    setMeDisplay("(not logged in)");
    setPlayerDisplay(null);
    setError("Not authenticated. Go back to main page and click Login.");
    return;
  }

  setMeDisplay(me.username);
  connectWs(room);
})();
