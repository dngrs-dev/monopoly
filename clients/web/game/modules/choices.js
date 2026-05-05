import { elements, state } from "./context.js";
import { isMyChoice } from "./game_state.js";
import { sendChoice } from "./actions.js";

export function renderChoices(choiceList) {
  const root = elements.choices;
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
    btn.textContent = `${c?.type || "Choice"} (${String(item?.id || "").slice(
      0,
      8,
    )})`;
    btn.disabled =
      !mine ||
      !state.ws ||
      state.ws.readyState !== WebSocket.OPEN ||
      state.tradeState.open;

    btn.onclick = () => {
      if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
      if (!mine) return;
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
