import { elements, state } from "./context.js";

export function sendChoice(choiceId, payload) {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  if (!choiceId) return;

  const room = elements.room?.value || "room1";
  const msg = {
    type: "choose",
    room_id: room,
    choice_id: choiceId,
  };
  if (payload !== undefined) msg.payload = payload;

  state.ws.send(JSON.stringify(msg));
}
