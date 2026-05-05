import { state } from "./ws_client/context.js";
import { updateOwnerCountdown } from "./ws_client/render.js";
import { checkAuth } from "./ws_client/auth.js";
import { wireEvents } from "./ws_client/events.js";

wireEvents();

if (!state.countdownTimer) {
  state.countdownTimer = window.setInterval(updateOwnerCountdown, 1000);
}

checkAuth();
