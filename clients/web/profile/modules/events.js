import {
  elements,
  state,
  setStatus,
  setError,
  openUsernameEditor,
  closeUsernameEditor,
} from "./context.js";
import { saveAvatar, clearAvatar } from "./avatar.js";
import { saveUsername } from "./username.js";

export function wireEvents() {
  if (elements.avatarInput) {
    elements.avatarInput.addEventListener("change", () => {
      setStatus("");
      setError("");
      const file = elements.avatarInput.files?.[0];
      if (!file) return;
      saveAvatar(file);
      elements.avatarInput.value = "";
    });
  }

  if (elements.avatarClear) {
    elements.avatarClear.addEventListener("click", () => {
      setStatus("");
      setError("");
      clearAvatar();
    });
  }

  if (elements.editUsernameBtn) {
    elements.editUsernameBtn.addEventListener("click", () => {
      if (!state.profileData?.is_self) return;
      setStatus("");
      setError("");
      if (elements.usernameInput)
        elements.usernameInput.value = state.profileData.username || "";
      openUsernameEditor();
    });
  }

  if (elements.cancelUsernameBtn) {
    elements.cancelUsernameBtn.addEventListener("click", () => {
      setStatus("");
      setError("");
      closeUsernameEditor();
    });
  }

  if (elements.saveUsernameBtn) {
    elements.saveUsernameBtn.addEventListener("click", () => {
      setStatus("");
      setError("");
      saveUsername();
    });
  }

  if (elements.backLobbyBtn) {
    elements.backLobbyBtn.addEventListener("click", () => {
      window.location.href = "/";
    });
  }
}
