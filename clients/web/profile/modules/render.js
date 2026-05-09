import { setText } from "../../shared/dom.js";
import {
  elements,
  state,
  setAvatarControlsEnabled,
  setUsernameControlsEnabled,
  closeUsernameEditor,
  setError,
} from "./context.js";
import { fetchProfile, fetchInventory } from "./api.js";
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

function renderInventory(cards) {
  if (!elements.inventoryContainer) return;
  elements.inventoryContainer.innerHTML = "";

  if (!Array.isArray(cards) || cards.length === 0) {
    setText(elements.inventoryContainer, "(no cards)");
    return;
  }

  const ul = document.createElement("ul");
  ul.style.listStyle = "none";
  ul.style.padding = "0";

  for (const card of cards) {
    const li = document.createElement("li");
    li.style.marginBottom = "12px";
    li.style.padding = "8px";
    li.style.border = "1px solid #ccc";
    li.style.borderRadius = "4px";
    
    const title = document.createElement("strong");
    title.textContent = card.name;
    
    const rarity = document.createElement("span");
    rarity.textContent = ` (${card.rarity.name})`;
    rarity.style.color = card.rarity.color;
    rarity.style.marginLeft = "8px";
    
    const description = document.createElement("div");
    description.textContent = card.description;
    description.style.fontSize = "0.9em";
    description.style.color = "#666";
    description.style.marginTop = "4px";
    
    li.appendChild(title);
    li.appendChild(rarity);
    li.appendChild(description);
    ul.appendChild(li);
  }

  elements.inventoryContainer.appendChild(ul);
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

  // Fetch and render inventory (only if viewing own profile)
  if (state.profileData.is_self) {
    const cards = await fetchInventory("en");
    if (cards !== null) {
      renderInventory(cards);
    }
  }
}
