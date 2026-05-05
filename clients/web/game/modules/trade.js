import { elements, state } from "./context.js";
import {
  getOwnedProperties,
  getPlayerBalance,
  getPlayerLabel,
} from "./game_state.js";
import { sendChoice } from "./actions.js";

function setTradeError(text) {
  if (elements.tradeError) elements.tradeError.textContent = text || "";
}

export function resetTradeState() {
  const tradeState = state.tradeState;
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

export function updateTradeState(choiceList) {
  if (!Array.isArray(choiceList)) {
    resetTradeState();
    return;
  }

  const tradeState = state.tradeState;
  const sendItem = choiceList.find(
    (item) =>
      item?.choice?.type === "SendTradeOfferChoice" &&
      item?.choice?.player_id === state.myPlayerId,
  );
  const acceptItem = choiceList.find(
    (item) =>
      item?.choice?.type === "AcceptTradeOfferChoice" &&
      item?.choice?.player_id === state.myPlayerId,
  );
  const rejectItem = choiceList.find(
    (item) =>
      item?.choice?.type === "RejectTradeOfferChoice" &&
      item?.choice?.player_id === state.myPlayerId,
  );

  if (sendItem) {
    if (state.dismissedSendChoiceId === sendItem.id) {
      return;
    }
    state.dismissedSendChoiceId = null;
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
    state.dismissedSendChoiceId = null;
    tradeState.open = true;
    tradeState.mode = "incoming";
    tradeState.sendChoiceId = null;
    tradeState.sendChoice = null;
    tradeState.acceptChoiceId = acceptItem?.id || null;
    tradeState.rejectChoiceId = rejectItem?.id || null;
    tradeState.sending = false;

    const offer = state.lastSnapshot?.trade_offer || null;
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
  state.dismissedSendChoiceId = null;
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

export function renderTradePanel() {
  if (!elements.tradePanel) return;

  const tradeState = state.tradeState;
  if (!tradeState.open || !state.lastSnapshot) {
    elements.tradePanel.hidden = true;
    setTradeError("");
    return;
  }

  elements.tradePanel.hidden = false;
  setTradeError("");

  const isOfferMode = tradeState.mode === "offer";
  const isIncomingMode = tradeState.mode === "incoming";

  let offeringPlayerId = null;
  let receivingPlayerId = null;

  if (isOfferMode) {
    offeringPlayerId = tradeState.sendChoice?.player_id ?? null;
    receivingPlayerId = tradeState.sendChoice?.receiving_player_id ?? null;
  } else if (isIncomingMode) {
    const offer = state.lastSnapshot.trade_offer || null;
    offeringPlayerId = offer?.offering_player_id ?? null;
    receivingPlayerId = offer?.receiving_player_id ?? null;
  }

  if (elements.tradeTitle) {
    elements.tradeTitle.textContent = isOfferMode
      ? `Trade with ${getPlayerLabel(receivingPlayerId)}`
      : "Incoming trade";
  }
  if (elements.tradeSubtitle) {
    if (!offeringPlayerId || !receivingPlayerId) {
      elements.tradeSubtitle.textContent = "";
    } else {
      elements.tradeSubtitle.textContent = `${getPlayerLabel(
        offeringPlayerId,
      )} -> ${getPlayerLabel(receivingPlayerId)}`;
    }
  }

  const offeredMax = offeringPlayerId ? getPlayerBalance(offeringPlayerId) : 0;
  const requestedMax = receivingPlayerId
    ? getPlayerBalance(receivingPlayerId)
    : 0;

  if (elements.tradeOfferedMoneyInput) {
    elements.tradeOfferedMoneyInput.disabled = !isOfferMode || tradeState.sending;
    elements.tradeOfferedMoneyInput.min = "0";
    elements.tradeOfferedMoneyInput.max = String(offeredMax);
    elements.tradeOfferedMoneyInput.value = String(tradeState.offeredMoney || 0);
    elements.tradeOfferedMoneyInput.oninput = () => {
      const next = clampMoney(elements.tradeOfferedMoneyInput.value, offeredMax);
      tradeState.offeredMoney = next;
      elements.tradeOfferedMoneyInput.value = String(next);
    };
  }

  if (elements.tradeRequestedMoneyInput) {
    elements.tradeRequestedMoneyInput.disabled =
      !isOfferMode || tradeState.sending;
    elements.tradeRequestedMoneyInput.min = "0";
    elements.tradeRequestedMoneyInput.max = String(requestedMax);
    elements.tradeRequestedMoneyInput.value = String(
      tradeState.requestedMoney || 0,
    );
    elements.tradeRequestedMoneyInput.oninput = () => {
      const next = clampMoney(
        elements.tradeRequestedMoneyInput.value,
        requestedMax,
      );
      tradeState.requestedMoney = next;
      elements.tradeRequestedMoneyInput.value = String(next);
    };
  }

  if (elements.tradeOfferedMax) {
    elements.tradeOfferedMax.textContent = offeredMax ? `max ${offeredMax}` : "";
  }
  if (elements.tradeRequestedMax) {
    elements.tradeRequestedMax.textContent =
      requestedMax ? `max ${requestedMax}` : "";
  }

  const offeredProps = offeringPlayerId
    ? getOwnedProperties(offeringPlayerId)
    : [];
  const requestedProps = receivingPlayerId
    ? getOwnedProperties(receivingPlayerId)
    : [];

  renderPropertyButtons(
    elements.tradeOfferedButtons,
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
    elements.tradeRequestedButtons,
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
    elements.tradeOfferedList,
    offeredProps,
    tradeState.offeredPositions,
    isOfferMode && !tradeState.sending,
    (pos) => {
      tradeState.offeredPositions.delete(pos);
      renderTradePanel();
    },
  );

  renderSelectedList(
    elements.tradeRequestedList,
    requestedProps,
    tradeState.requestedPositions,
    isOfferMode && !tradeState.sending,
    (pos) => {
      tradeState.requestedPositions.delete(pos);
      renderTradePanel();
    },
  );

  if (elements.tradeAcceptBtn) {
    elements.tradeAcceptBtn.textContent = "Accept";
    elements.tradeAcceptBtn.disabled =
      tradeState.sending ||
      (!isOfferMode && !tradeState.acceptChoiceId) ||
      !state.ws ||
      state.ws.readyState !== WebSocket.OPEN;
  }

  if (elements.tradeCloseBtn) {
    elements.tradeCloseBtn.textContent = "Close";
    elements.tradeCloseBtn.disabled = tradeState.sending;
  }
}

export function sendTradeOffer() {
  const tradeState = state.tradeState;
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

export function acceptTradeOffer() {
  const tradeState = state.tradeState;
  if (!tradeState.acceptChoiceId) return;
  tradeState.sending = true;
  sendChoice(tradeState.acceptChoiceId);
  renderTradePanel();
}

export function rejectTradeOffer() {
  const tradeState = state.tradeState;
  if (!tradeState.rejectChoiceId) return;
  tradeState.sending = true;
  sendChoice(tradeState.rejectChoiceId);
  renderTradePanel();
}
