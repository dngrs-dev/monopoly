let ws = null;
let lastSnapshot = null;
let myPlayerId = null;
let lastChoices = [];
let dismissedSendChoiceId = null;

const tradeState = {
  open: false,
  mode: null,
  sendChoiceId: null,
  sendChoice: null,
  acceptChoiceId: null,
  rejectChoiceId: null,
  offeredMoney: 0,
  requestedMoney: 0,
  offeredPositions: new Set(),
  requestedPositions: new Set(),
  sending: false,
};

const $ = (id) => document.getElementById(id);

const playersRoot = $("players");
const tradePanel = $("trade-panel");
const tradeTitle = $("trade-title");
const tradeSubtitle = $("trade-subtitle");
const tradeError = $("trade-error");
const tradeOfferedMoneyInput = $("trade-offered-money");
const tradeRequestedMoneyInput = $("trade-requested-money");
const tradeOfferedMax = $("trade-offered-max");
const tradeRequestedMax = $("trade-requested-max");
const tradeOfferedButtons = $("trade-offered-buttons");
const tradeRequestedButtons = $("trade-requested-buttons");
const tradeOfferedList = $("trade-offered-list");
const tradeRequestedList = $("trade-requested-list");
const tradeAcceptBtn = $("trade-accept");
const tradeCloseBtn = $("trade-close");

function setStatus(text) {
  const el = $("status");
  if (el) el.textContent = text;
}

function setError(text) {
  const el = $("err");
  if (el) el.textContent = text || "";
}

function setTradeError(text) {
  if (tradeError) tradeError.textContent = text || "";
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

function getPlayerById(playerId) {
  const players = Array.isArray(lastSnapshot?.players)
    ? lastSnapshot.players
    : [];
  return players.find((p) => p?.id === playerId) || null;
}

function getPlayerBalance(playerId) {
  const player = getPlayerById(playerId);
  return Number.isFinite(player?.balance) ? player.balance : 0;
}

function getPlayerLabel(playerId) {
  return `Player ${playerId}`;
}

function getOwnedProperties(playerId) {
  const tiles = Array.isArray(lastSnapshot?.tiles) ? lastSnapshot.tiles : [];
  const props = [];

  for (let pos = 0; pos < tiles.length; pos++) {
    const t = tiles[pos];
    if (!t || typeof t !== "object") continue;
    if (!("owner" in t)) continue;
    if (t.owner !== playerId) continue;
    props.push({ pos, name: t.name || `Property ${pos}` });
  }

  return props;
}

function resetTradeState() {
  tradeState.open = false;
  tradeState.mode = null;
  tradeState.sendChoiceId = null;
  tradeState.sendChoice = null;
  tradeState.acceptChoiceId = null;
  tradeState.rejectChoiceId = null;
  tradeState.offeredMoney = 0;
  tradeState.requestedMoney = 0;
  tradeState.offeredPositions = new Set();
  tradeState.requestedPositions = new Set();
  tradeState.sending = false;
}

function clampMoney(value, maxValue) {
  const raw = Number.parseInt(value, 10);
  if (!Number.isFinite(raw)) return 0;
  if (raw < 0) return 0;
  if (Number.isFinite(maxValue) && raw > maxValue) return maxValue;
  return raw;
}

function updateTradeState(choiceList) {
  if (!Array.isArray(choiceList)) {
    resetTradeState();
    return;
  }

  const sendItem = choiceList.find(
    (item) =>
      item?.choice?.type === "SendTradeOfferChoice" &&
      item?.choice?.player_id === myPlayerId,
  );
  const acceptItem = choiceList.find(
    (item) =>
      item?.choice?.type === "AcceptTradeOfferChoice" &&
      item?.choice?.player_id === myPlayerId,
  );
  const rejectItem = choiceList.find(
    (item) =>
      item?.choice?.type === "RejectTradeOfferChoice" &&
      item?.choice?.player_id === myPlayerId,
  );

  if (sendItem) {
    if (dismissedSendChoiceId === sendItem.id) {
      return;
    }
    dismissedSendChoiceId = null;
    const sameChoice =
      tradeState.open &&
      tradeState.mode === "offer" &&
      tradeState.sendChoiceId === sendItem.id;

    tradeState.open = true;
    tradeState.mode = "offer";
    tradeState.sendChoiceId = sendItem.id;
    tradeState.sendChoice = sendItem.choice;
    tradeState.acceptChoiceId = null;
    tradeState.rejectChoiceId = null;

    if (!sameChoice) {
      tradeState.offeredMoney = 0;
      tradeState.requestedMoney = 0;
      tradeState.offeredPositions = new Set();
      tradeState.requestedPositions = new Set();
      tradeState.sending = false;
    }
    return;
  }

  if (acceptItem || rejectItem) {
    dismissedSendChoiceId = null;
    tradeState.open = true;
    tradeState.mode = "incoming";
    tradeState.sendChoiceId = null;
    tradeState.sendChoice = null;
    tradeState.acceptChoiceId = acceptItem?.id || null;
    tradeState.rejectChoiceId = rejectItem?.id || null;
    tradeState.sending = false;

    const offer = lastSnapshot?.trade_offer || null;
    tradeState.offeredMoney = Number.isFinite(offer?.offered_money)
      ? offer.offered_money
      : 0;
    tradeState.requestedMoney = Number.isFinite(offer?.requested_money)
      ? offer.requested_money
      : 0;
    tradeState.offeredPositions = new Set(
      Array.isArray(offer?.offered_properties_positions)
        ? offer.offered_properties_positions
        : [],
    );
    tradeState.requestedPositions = new Set(
      Array.isArray(offer?.requested_properties_positions)
        ? offer.requested_properties_positions
        : [],
    );
    return;
  }

  resetTradeState();
  dismissedSendChoiceId = null;
}

function renderPropertyButtons(
  root,
  properties,
  selectedSet,
  disabled,
  onToggle,
) {
  if (!root) return;
  root.innerHTML = "";

  if (!properties || properties.length === 0) {
    root.textContent = "(none)";
    return;
  }

  for (const prop of properties) {
    const selected = selectedSet.has(prop.pos);
    const btn = document.createElement("button");
    btn.textContent = `${selected ? "Remove" : "Add"} ${prop.name} (#${
      prop.pos
    })`;
    btn.disabled = disabled;
    btn.onclick = () => onToggle(prop.pos);
    root.appendChild(btn);
  }
}

function renderSelectedList(root, properties, selectedSet, allowRemove, onRemove) {
  if (!root) return;
  root.innerHTML = "";

  const byPos = new Map(properties.map((prop) => [prop.pos, prop]));
  const positions = Array.from(selectedSet.values());

  if (positions.length === 0) {
    root.textContent = "(none)";
    return;
  }

  for (const pos of positions) {
    const prop = byPos.get(pos);
    const name = prop ? `${prop.name} (#${prop.pos})` : `Property ${pos}`;
    const li = document.createElement("li");
    li.textContent = name;
    if (allowRemove) {
      const btn = document.createElement("button");
      btn.textContent = "Remove";
      btn.onclick = () => onRemove(pos);
      li.appendChild(btn);
    }
    root.appendChild(li);
  }
}

function renderTradePanel() {
  if (!tradePanel) return;

  if (!tradeState.open || !lastSnapshot) {
    tradePanel.hidden = true;
    setTradeError("");
    return;
  }

  tradePanel.hidden = false;
  setTradeError("");

  const isOfferMode = tradeState.mode === "offer";
  const isIncomingMode = tradeState.mode === "incoming";

  let offeringPlayerId = null;
  let receivingPlayerId = null;

  if (isOfferMode) {
    offeringPlayerId = tradeState.sendChoice?.player_id ?? null;
    receivingPlayerId = tradeState.sendChoice?.receiving_player_id ?? null;
  } else if (isIncomingMode) {
    const offer = lastSnapshot.trade_offer || null;
    offeringPlayerId = offer?.offering_player_id ?? null;
    receivingPlayerId = offer?.receiving_player_id ?? null;
  }

  if (tradeTitle) {
    tradeTitle.textContent = isOfferMode
      ? `Trade with ${getPlayerLabel(receivingPlayerId)}`
      : "Incoming trade";
  }
  if (tradeSubtitle) {
    if (!offeringPlayerId || !receivingPlayerId) {
      tradeSubtitle.textContent = "";
    } else {
      tradeSubtitle.textContent = `${getPlayerLabel(
        offeringPlayerId,
      )} -> ${getPlayerLabel(receivingPlayerId)}`;
    }
  }

  const offeredMax = offeringPlayerId ? getPlayerBalance(offeringPlayerId) : 0;
  const requestedMax = receivingPlayerId
    ? getPlayerBalance(receivingPlayerId)
    : 0;

  if (tradeOfferedMoneyInput) {
    tradeOfferedMoneyInput.disabled = !isOfferMode || tradeState.sending;
    tradeOfferedMoneyInput.min = "0";
    tradeOfferedMoneyInput.max = String(offeredMax);
    tradeOfferedMoneyInput.value = String(tradeState.offeredMoney || 0);
    tradeOfferedMoneyInput.oninput = () => {
      const next = clampMoney(tradeOfferedMoneyInput.value, offeredMax);
      tradeState.offeredMoney = next;
      tradeOfferedMoneyInput.value = String(next);
    };
  }

  if (tradeRequestedMoneyInput) {
    tradeRequestedMoneyInput.disabled = !isOfferMode || tradeState.sending;
    tradeRequestedMoneyInput.min = "0";
    tradeRequestedMoneyInput.max = String(requestedMax);
    tradeRequestedMoneyInput.value = String(tradeState.requestedMoney || 0);
    tradeRequestedMoneyInput.oninput = () => {
      const next = clampMoney(tradeRequestedMoneyInput.value, requestedMax);
      tradeState.requestedMoney = next;
      tradeRequestedMoneyInput.value = String(next);
    };
  }

  if (tradeOfferedMax) {
    tradeOfferedMax.textContent = offeredMax ? `max ${offeredMax}` : "";
  }
  if (tradeRequestedMax) {
    tradeRequestedMax.textContent = requestedMax ? `max ${requestedMax}` : "";
  }

  const offeredProps = offeringPlayerId
    ? getOwnedProperties(offeringPlayerId)
    : [];
  const requestedProps = receivingPlayerId
    ? getOwnedProperties(receivingPlayerId)
    : [];

  renderPropertyButtons(
    tradeOfferedButtons,
    offeredProps,
    tradeState.offeredPositions,
    !isOfferMode || tradeState.sending,
    (pos) => {
      if (tradeState.offeredPositions.has(pos)) {
        tradeState.offeredPositions.delete(pos);
      } else {
        tradeState.offeredPositions.add(pos);
      }
      renderTradePanel();
    },
  );

  renderPropertyButtons(
    tradeRequestedButtons,
    requestedProps,
    tradeState.requestedPositions,
    !isOfferMode || tradeState.sending,
    (pos) => {
      if (tradeState.requestedPositions.has(pos)) {
        tradeState.requestedPositions.delete(pos);
      } else {
        tradeState.requestedPositions.add(pos);
      }
      renderTradePanel();
    },
  );

  renderSelectedList(
    tradeOfferedList,
    offeredProps,
    tradeState.offeredPositions,
    isOfferMode && !tradeState.sending,
    (pos) => {
      tradeState.offeredPositions.delete(pos);
      renderTradePanel();
    },
  );

  renderSelectedList(
    tradeRequestedList,
    requestedProps,
    tradeState.requestedPositions,
    isOfferMode && !tradeState.sending,
    (pos) => {
      tradeState.requestedPositions.delete(pos);
      renderTradePanel();
    },
  );

  if (tradeAcceptBtn) {
    tradeAcceptBtn.textContent = "Accept";
    tradeAcceptBtn.disabled =
      tradeState.sending ||
      (!isOfferMode && !tradeState.acceptChoiceId) ||
      !ws ||
      ws.readyState !== WebSocket.OPEN;
  }

  if (tradeCloseBtn) {
    tradeCloseBtn.textContent = "Close";
    tradeCloseBtn.disabled = tradeState.sending;
  }
}

function renderPlayers(choiceList) {
  if (!playersRoot) return;
  playersRoot.innerHTML = "";

  if (!lastSnapshot || !Array.isArray(lastSnapshot.players)) {
    playersRoot.textContent = "(none)";
    return;
  }

  const isMyTurn = lastSnapshot.current_player_id === myPlayerId;
  const tradeChoices = new Map();

  if (Array.isArray(choiceList)) {
    for (const item of choiceList) {
      const c = item?.choice;
      if (
        c?.type === "MakeTradeOfferChoice" &&
        c.player_id === myPlayerId &&
        Number.isInteger(c.receiving_player_id)
      ) {
        tradeChoices.set(c.receiving_player_id, item.id);
      }
    }
  }

  for (const player of lastSnapshot.players) {
    const row = document.createElement("div");
    const isCurrent = player?.id === lastSnapshot.current_player_id;
    const isMe = player?.id === myPlayerId;
    const labelParts = [
      `Player ${player?.id ?? "?"}`,
      `balance ${player?.balance ?? "?"}`,
    ];
    if (isCurrent) labelParts.push("turn");
    if (isMe) labelParts.push("you");
    row.appendChild(document.createTextNode(labelParts.join(" | ")));

    const canTrade =
      isMyTurn &&
      player?.id !== myPlayerId &&
      tradeChoices.has(player?.id);

    if (canTrade) {
      const btn = document.createElement("button");
      btn.textContent = "Trade";
      btn.disabled =
        tradeState.open ||
        tradeState.sending ||
        !ws ||
        ws.readyState !== WebSocket.OPEN;
      btn.onclick = () => {
        const choiceId = tradeChoices.get(player.id);
        if (!choiceId) return;
        sendChoice(choiceId);
      };
      row.appendChild(btn);
    }

    playersRoot.appendChild(row);
  }
}

function renderChoices(choiceList) {
  const root = $("choices");
  if (!root) return;

  root.innerHTML = "";

  if (!Array.isArray(choiceList) || choiceList.length === 0) {
    root.textContent = "(none)";
    return;
  }

  const hiddenTypes = new Set([
    "MakeTradeOfferChoice",
    "SendTradeOfferChoice",
    "AcceptTradeOfferChoice",
    "RejectTradeOfferChoice",
  ]);

  const visibleChoices = choiceList.filter(
    (item) => !hiddenTypes.has(item?.choice?.type),
  );

  if (visibleChoices.length === 0) {
    root.textContent = "(none)";
    return;
  }

  for (const item of visibleChoices) {
    const c = item?.choice;
    const mine = isMyChoice(c);

    const btn = document.createElement("button");
    btn.textContent = `${c?.type || "Choice"} (${String(item?.id || "").slice(0, 8)})`;
    btn.disabled =
      !mine ||
      !ws ||
      ws.readyState !== WebSocket.OPEN ||
      tradeState.open;

    btn.onclick = () => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      if (!mine) return;

      const room = $("room")?.value || "room1";
      sendChoice(item.id);
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
    lastChoices = data.choices || [];
    updateTradeState(lastChoices);
    renderPlayers(lastChoices);
    renderTradePanel();
    renderChoices(lastChoices);
    return;
  }

  if (data?.type === "update") {
    lastSnapshot = data.snapshot ?? null;
    renderJson($("snapshot"), lastSnapshot);
    renderJson($("events"), data.events ?? null);
    lastChoices = data.choices || [];
    updateTradeState(lastChoices);
    renderPlayers(lastChoices);
    renderTradePanel();
    renderChoices(lastChoices);
    return;
  }
}

function sendChoice(choiceId, payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!choiceId) return;

  const room = $("room")?.value || "room1";
  const msg = {
    type: "choose",
    room_id: room,
    choice_id: choiceId,
  };
  if (payload !== undefined) msg.payload = payload;

  ws.send(JSON.stringify(msg));
}

function sendTradeOffer() {
  if (!tradeState.sendChoiceId || !tradeState.sendChoice) return;
  const offeringId = tradeState.sendChoice.player_id;
  const receivingId = tradeState.sendChoice.receiving_player_id;
  const offeredMax = getPlayerBalance(offeringId);
  const requestedMax = getPlayerBalance(receivingId);

  const offeredMoney = clampMoney(tradeState.offeredMoney, offeredMax);
  const requestedMoney = clampMoney(tradeState.requestedMoney, requestedMax);

  tradeState.offeredMoney = offeredMoney;
  tradeState.requestedMoney = requestedMoney;

  const payload = {
    offered_money: offeredMoney,
    requested_money: requestedMoney,
    offered_properties_positions: Array.from(tradeState.offeredPositions.values()),
    requested_properties_positions: Array.from(
      tradeState.requestedPositions.values(),
    ),
  };

  tradeState.sending = true;
  sendChoice(tradeState.sendChoiceId, payload);
  renderTradePanel();
}

function acceptTradeOffer() {
  if (!tradeState.acceptChoiceId) return;
  tradeState.sending = true;
  sendChoice(tradeState.acceptChoiceId);
  renderTradePanel();
}

function rejectTradeOffer() {
  if (!tradeState.rejectChoiceId) return;
  tradeState.sending = true;
  sendChoice(tradeState.rejectChoiceId);
  renderTradePanel();
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

if (tradeAcceptBtn) {
  tradeAcceptBtn.onclick = () => {
    if (!tradeState.open) return;
    if (tradeState.mode === "offer") {
      sendTradeOffer();
      return;
    }
    if (tradeState.mode === "incoming") {
      acceptTradeOffer();
    }
  };
}

if (tradeCloseBtn) {
  tradeCloseBtn.onclick = () => {
    if (!tradeState.open) return;
    if (tradeState.mode === "incoming") {
      rejectTradeOffer();
      return;
    }

    dismissedSendChoiceId = tradeState.sendChoiceId;
    resetTradeState();
    renderTradePanel();
    renderPlayers(lastChoices);
    renderChoices(lastChoices);
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
