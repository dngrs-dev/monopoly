import {
  elements,
  state,
  setError,
  renderJson,
  setPlayerDisplay,
} from "./context.js";
import { updateTradeState, renderTradePanel } from "./trade.js";
import { renderPlayers } from "./players.js";
import { renderChoices } from "./choices.js";

export function onMessage(data) {
  setError("");

  if (data?.type === "error") {
    setError(data.message);
    return;
  }

  if (data?.type === "joined") {
    state.myPlayerId = data.you?.player_id ?? null;
    setPlayerDisplay(state.myPlayerId);

    state.lastSnapshot = data.snapshot ?? null;
    renderJson(elements.snapshot, state.lastSnapshot);
    renderJson(elements.events, null);
    state.lastChoices = data.choices || [];
    updateTradeState(state.lastChoices);
    renderPlayers(state.lastChoices);
    renderTradePanel();
    renderChoices(state.lastChoices);
    return;
  }

  if (data?.type === "update") {
    state.lastSnapshot = data.snapshot ?? null;
    renderJson(elements.snapshot, state.lastSnapshot);
    renderJson(elements.events, data.events ?? null);
    state.lastChoices = data.choices || [];
    updateTradeState(state.lastChoices);
    renderPlayers(state.lastChoices);
    renderTradePanel();
    renderChoices(state.lastChoices);
    return;
  }
}
