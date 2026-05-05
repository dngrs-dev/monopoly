import { elements, state } from "./context.js";
import {
  acceptTradeOffer,
  rejectTradeOffer,
  renderTradePanel,
  resetTradeState,
  sendTradeOffer,
} from "./trade.js";
import { renderPlayers } from "./players.js";
import { renderChoices } from "./choices.js";

export function wireEvents() {
  if (elements.disconnect) {
    elements.disconnect.onclick = () => {
      try {
        if (state.ws) state.ws.close();
      } catch {}
      window.location.href = "/";
    };
  }

  if (elements.tradeAcceptBtn) {
    elements.tradeAcceptBtn.onclick = () => {
      if (!state.tradeState.open) return;
      if (state.tradeState.mode === "offer") {
        sendTradeOffer();
        return;
      }
      if (state.tradeState.mode === "incoming") {
        acceptTradeOffer();
      }
    };
  }

  if (elements.tradeCloseBtn) {
    elements.tradeCloseBtn.onclick = () => {
      if (!state.tradeState.open) return;
      if (state.tradeState.mode === "incoming") {
        rejectTradeOffer();
        return;
      }

      state.dismissedSendChoiceId = state.tradeState.sendChoiceId;
      resetTradeState();
      renderTradePanel();
      renderPlayers(state.lastChoices);
      renderChoices(state.lastChoices);
    };
  }
}
