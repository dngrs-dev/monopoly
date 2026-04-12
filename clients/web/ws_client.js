let ws = null;
let lastRoom = null;
let lastSnapshot = null;
let lastSendTradeChoice = null;

const $ = (id) => document.getElementById(id);

function setStatus(text) {
  $("status").textContent = text;
}

function setError(text) {
  $("err").textContent = text || "";
}

function renderJson(el, obj) {
  el.textContent = obj ? JSON.stringify(obj, null, 2) : "(none)";
}

function renderChoices(choiceList) {
  const root = $("choices");
  root.innerHTML = "";

  lastSendTradeChoice = null;
  for (const item of choiceList || []) {
    if (item.choice?.type === "SendTradeOfferChoice") {
      lastSendTradeChoice = item.choice;
      break;
    }
  }
  renderTradePanel(lastSendTradeChoice);

  if (!choiceList || choiceList.length === 0) {
    root.textContent = "(none)";
    return;
  }

  for (const item of choiceList) {
    const btn = document.createElement("button");
    btn.textContent = `${item.choice?.type || "Choice"} (${item.id.slice(0, 8)})`;
    btn.onclick = () => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const room = $("room").value;
      const player = parseInt($("player").value, 10);

      let payload = undefined;

      if (item.choice?.type === "SendTradeOfferChoice") {
        const offered_money = parseInt($("trade_offered_money").value, 10) || 0;
        const requested_money =
          parseInt($("trade_requested_money").value, 10) || 0;

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

      ws.send(
        JSON.stringify({
          type: "choose",
          room_id: room,
          player_id: player,
          choice_id: item.id,
          payload,
        }),
      );
    };

    const details = document.createElement("span");
    details.style.marginLeft = "6px";
    details.style.fontSize = "12px";
    details.textContent = JSON.stringify(item.choice);

    const line = document.createElement("div");
    line.appendChild(btn);
    line.appendChild(details);
    root.appendChild(line);
  }
}

function onMessage(data) {
  setError(null);

  if (data.type === "error") {
    setError(data.message);
    return;
  }

  if (data.type === "joined") {
    lastSnapshot = data.snapshot;
    renderJson($("snapshot"), data.snapshot);
    renderJson($("events"), null);
    renderChoices(data.choices);
    return;
  }

  if (data.type === "update") {
    lastSnapshot = data.snapshot;
    renderJson($("snapshot"), data.snapshot);
    renderJson($("events"), data.events);
    renderChoices(data.choices);
    return;
  }
}

$("connect").onclick = () => {
  setError(null);

  const room = $("room").value;
  const player = parseInt($("player").value, 10);

  if (!room) {
    setError("Room is required");
    return;
  }
  if (!player || player < 1) {
    setError("Player must be >= 1");
    return;
  }

  const url = new URL(window.location.href);
  const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProto}//${url.host}/ws`;

  ws = new WebSocket(wsUrl);
  lastRoom = room;

  ws.onopen = () => {
    setStatus("connected");
    $("connect").disabled = true;
    $("disconnect").disabled = false;
    ws.send(JSON.stringify({ type: "join", room_id: room, player_id: player }));
  };

  ws.onmessage = (evt) => {
    try {
      onMessage(JSON.parse(evt.data));
    } catch (e) {
      setError("Bad JSON from server");
    }
  };

  ws.onclose = () => {
    setStatus("disconnected");
    $("connect").disabled = false;
    $("disconnect").disabled = true;
  };

  ws.onerror = () => {
    setError("WebSocket error");
  };
};

$("disconnect").onclick = () => {
  if (ws) ws.close();
};

function renderTradePanel(sendChoice) {
  const offeredRoot = $("trade_offered_props");
  const requestedRoot = $("trade_requested_props");

  offeredRoot.innerHTML = "";
  requestedRoot.innerHTML = "";

  if (!lastSnapshot || !sendChoice) {
    offeredRoot.textContent = "(none)";
    requestedRoot.textContent = "(none)";
    return;
  }

  const tiles = lastSnapshot.tiles || [];

  const offered = [];
  const requested = [];

  for (let pos = 0; pos < tiles.length; pos++) {
    const t = tiles[pos];
    if (!t || t.type !== "PropertyTile") continue;

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
