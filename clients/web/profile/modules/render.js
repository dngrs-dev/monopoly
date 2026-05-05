import { setText } from "../../shared/dom.js";
import {
  elements,
  state,
  setAvatarControlsEnabled,
  setUsernameControlsEnabled,
  closeUsernameEditor,
  setError,
} from "./context.js";
import { fetchProfile } from "./api.js";
import { loadAvatar } from "./avatar.js";

function renderHistory(history, show) {
  if (!elements.usernameHistoryEl) return;
  elements.usernameHistoryEl.innerHTML = "";

  if (!show) {
    setText(elements.usernameHistoryEl, "(hidden)");
    return;
  }

  if (!Array.isArray(history) || history.length === 0) {
    setText(elements.usernameHistoryEl, "(none)");
    return;
  }

  for (const item of history) {
    const li = document.createElement("li");
    li.textContent = item.username || "(unknown)";
    elements.usernameHistoryEl.appendChild(li);
  }
}

function renderStats(stats) {
  setText(elements.statsPlayedEl, String(stats?.games_played ?? 0));
  setText(elements.statsWinsEl, String(stats?.wins ?? 0));
}

export function renderProfile() {
  if (!state.profileData) return;

  const isSelf = !!state.profileData.is_self;

  setText(
    elements.currentUsernameEl,
    state.profileData.username || "(unknown)",
  );
  setText(elements.profileHandleEl, state.profileData.handle || "(unknown)");

  if (elements.profileLinkEl) {
    elements.profileLinkEl.textContent =
      state.profileData.profile_link || "(unknown)";
    elements.profileLinkEl.href = state.profileData.profile_link || "/profile";
  }

  renderStats(state.profileData.stats || { games_played: 0, wins: 0 });
  if (elements.usernameHistorySection)
    elements.usernameHistorySection.hidden = !isSelf;
  renderHistory(state.profileData.history, isSelf);

  setAvatarControlsEnabled(isSelf);
  setUsernameControlsEnabled(isSelf);
  if (elements.usernameInput)
    elements.usernameInput.value = state.profileData.username || "";
  closeUsernameEditor();
  loadAvatar(state.profileData, isSelf);
}

export async function refreshProfile() {
  state.profileData = await fetchProfile(state.viewingHandle);
  if (!state.profileData) {
    setError("Profile not found or not accessible");
    return;
  }
  renderProfile();
}
