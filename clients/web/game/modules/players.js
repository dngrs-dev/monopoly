import { elements, state } from "./context.js";
import { sendChoice } from "./actions.js";

export function renderPlayers(choiceList) {
  if (!elements.playersRoot) return;
  elements.playersRoot.innerHTML = "";

  if (!state.lastSnapshot || !Array.isArray(state.lastSnapshot.players)) {
    elements.playersRoot.textContent = "(none)";
    return;
  }

  const isMyTurn = state.lastSnapshot.current_player_id === state.myPlayerId;
  const tradeChoices = new Map();

  if (Array.isArray(choiceList)) {
    for (const item of choiceList) {
      const c = item?.choice;
      if (
        c?.type === "MakeTradeOfferChoice" &&
        c.player_id === state.myPlayerId &&
        Number.isInteger(c.receiving_player_id)
      ) {
        tradeChoices.set(c.receiving_player_id, item.id);
      }
    }
  }

  for (const player of state.lastSnapshot.players) {
    const row = document.createElement("div");
    const isCurrent = player?.id === state.lastSnapshot.current_player_id;
    const isMe = player?.id === state.myPlayerId;
    const labelParts = [
      `Player ${player?.id ?? "?"}`,
      `balance ${player?.balance ?? "?"}`,
    ];
    if (isCurrent) labelParts.push("turn");
    if (isMe) labelParts.push("you");
    row.appendChild(document.createTextNode(labelParts.join(" | ")));

    const canTrade =
      isMyTurn &&
      player?.id !== state.myPlayerId &&
      tradeChoices.has(player?.id);

    if (canTrade) {
      const btn = document.createElement("button");
      btn.textContent = "Trade";
      btn.disabled =
        state.tradeState.open ||
        state.tradeState.sending ||
        !state.ws ||
        state.ws.readyState !== WebSocket.OPEN;
      btn.onclick = () => {
        const choiceId = tradeChoices.get(player.id);
        if (!choiceId) return;
        sendChoice(choiceId);
      };
      row.appendChild(btn);
    }

    elements.playersRoot.appendChild(row);
  }
}
