import { setText } from "../shared/dom.js";
import {
  elements,
  state,
  setStatus,
  setError,
  setAvatarControlsEnabled,
  setUsernameControlsEnabled,
  getHandleFromPath,
} from "./modules/context.js";
import { fetchMe } from "./modules/api.js";
import { refreshProfile } from "./modules/render.js";
import { wireEvents } from "./modules/events.js";

wireEvents();

(async function start() {
  setStatus("Loading...");
  state.viewingHandle = getHandleFromPath();
  state.currentUser = await fetchMe();

  if (!state.currentUser) {
    setText(elements.currentUserEl, "(not signed in)");
    setText(elements.currentUsernameEl, "(not signed in)");
    setStatus("");
    setError("Not authenticated. Go back and sign in.");
    setAvatarControlsEnabled(false);
    setUsernameControlsEnabled(false);
    return;
  }

  setText(elements.currentUserEl, state.currentUser.username);
  setStatus("");
  await refreshProfile();
})();
