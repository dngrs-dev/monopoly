import {
  elements,
  setError,
  setMeDisplay,
  setPlayerDisplay,
  setStatus,
  getRoomFromUrl,
  fetchMe,
} from "./modules/context.js";
import { wireEvents } from "./modules/events.js";
import { connectWs } from "./modules/ws.js";

wireEvents();

(async function start() {
  setStatus("disconnected");

  const room = getRoomFromUrl();
  if (elements.room) {
    elements.room.value = room;
    elements.room.disabled = true; // no Connect button here, so don't let it mislead
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
