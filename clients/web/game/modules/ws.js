import { elements, state, setStatus, setError, setPlayerDisplay } from "./context.js";
import { onMessage } from "./message.js";

export function connectWs(room) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) state.ws.close();

  const url = new URL(window.location.href);
  const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProto}//${url.host}/ws`;

  state.ws = new WebSocket(wsUrl);

  state.ws.onopen = () => {
    setStatus("connected");
    if (elements.disconnect) elements.disconnect.disabled = false;

    state.myPlayerId = null;
    setPlayerDisplay(null);

    state.ws?.send(JSON.stringify({ type: "join", room_id: room }));
  };

  state.ws.onmessage = (evt) => {
    try {
      onMessage(JSON.parse(evt.data));
    } catch {
      setError("Bad JSON from server");
    }
  };

  state.ws.onclose = (evt) => {
    setStatus("disconnected");
    if (elements.disconnect) elements.disconnect.disabled = true;

    if (evt?.code === 1008) {
      setError("Not authenticated. Go to main page and click Login.");
    }
  };

  state.ws.onerror = () => {
    setError("WebSocket error");
  };
}
