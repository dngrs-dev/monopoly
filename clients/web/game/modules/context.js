import { $, setText } from "../../shared/dom.js";

export { $ };

export const elements = {
  playersRoot: $("players"),
  tradePanel: $("trade-panel"),
  tradeTitle: $("trade-title"),
  tradeSubtitle: $("trade-subtitle"),
  tradeError: $("trade-error"),
  tradeOfferedMoneyInput: $("trade-offered-money"),
  tradeRequestedMoneyInput: $("trade-requested-money"),
  tradeOfferedMax: $("trade-offered-max"),
  tradeRequestedMax: $("trade-requested-max"),
  tradeOfferedButtons: $("trade-offered-buttons"),
  tradeRequestedButtons: $("trade-requested-buttons"),
  tradeOfferedList: $("trade-offered-list"),
  tradeRequestedList: $("trade-requested-list"),
  tradeAcceptBtn: $("trade-accept"),
  tradeCloseBtn: $("trade-close"),
  status: $("status"),
  err: $("err"),
  me: $("me"),
  player: $("player"),
  room: $("room"),
  disconnect: $("disconnect"),
  choices: $("choices"),
  snapshot: $("snapshot"),
  events: $("events"),
};

export const state = {
  ws: null,
  lastSnapshot: null,
  myPlayerId: null,
  lastChoices: [],
  dismissedSendChoiceId: null,
  tradeState: {
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
  },
};

export function setStatus(text) {
  setText(elements.status, text);
}

export function setError(text) {
  setText(elements.err, text || "");
}

export function renderJson(el, obj) {
  if (!el) return;
  el.textContent = obj ? JSON.stringify(obj, null, 2) : "(none)";
}

export function setMeDisplay(username) {
  setText(elements.me, username || "(unknown)");
}

export function setPlayerDisplay(value) {
  setText(
    elements.player,
    value == null ? "(spectator)" : String(value),
  );
}

export function getRoomFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const room = (params.get("room") || "").trim();
  return room || "room1";
}

export async function fetchMe() {
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (res.status === 401) return null;
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
