let ws = null;
let lastRoom = null;

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
      ws.send(
        JSON.stringify({
          type: "choose",
          room_id: room,
          player_id: player,
          choice_id: item.id,
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
    renderJson($("snapshot"), data.snapshot);
    renderJson($("events"), null);
    renderChoices(data.choices);
    return;
  }

  if (data.type === "update") {
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
