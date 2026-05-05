import { $, setText } from "../../shared/dom.js";

export const elements = {
  currentUserEl: $("current-user"),
  currentUsernameEl: $("current-username"),
  profileHandleEl: $("profile-handle"),
  profileLinkEl: $("profile-link"),
  usernameHistorySection: $("username-history-section"),
  usernameHistoryEl: $("username-history"),
  statsPlayedEl: $("stats-played"),
  statsWinsEl: $("stats-wins"),
  statusEl: $("status"),
  errEl: $("err"),
  avatarPreview: $("avatar-preview"),
  avatarInput: $("avatar-input"),
  avatarClear: $("avatar-clear"),
  editUsernameBtn: $("edit-username"),
  usernameEditor: $("username-editor"),
  usernameInput: $("username-input"),
  saveUsernameBtn: $("save-username"),
  cancelUsernameBtn: $("cancel-username"),
  backLobbyBtn: $("back-lobby"),
};

export const constants = {
  MAX_AVATAR_BYTES: 1024 * 1024,
  AVATAR_SIZE: 256,
};

export const state = {
  currentUser: null,
  profileData: null,
  viewingHandle: null,
};

export function setError(text) {
  setText(elements.errEl, text || "");
}

export function setStatus(text) {
  setText(elements.statusEl, text || "");
}

export function setAvatarPreview(src) {
  if (!elements.avatarPreview) return;
  elements.avatarPreview.src = src || "";
}

export function setAvatarControlsEnabled(enabled) {
  if (elements.avatarInput) elements.avatarInput.disabled = !enabled;
  if (elements.avatarClear) elements.avatarClear.disabled = !enabled;
}

export function setUsernameControlsEnabled(enabled) {
  if (elements.editUsernameBtn) elements.editUsernameBtn.disabled = !enabled;
  if (elements.usernameInput) elements.usernameInput.disabled = !enabled;
  if (elements.saveUsernameBtn) elements.saveUsernameBtn.disabled = !enabled;
  if (elements.cancelUsernameBtn) elements.cancelUsernameBtn.disabled = !enabled;
}

export function openUsernameEditor() {
  if (elements.usernameEditor) elements.usernameEditor.hidden = false;
  if (elements.editUsernameBtn) elements.editUsernameBtn.disabled = true;
  if (elements.usernameInput) elements.usernameInput.focus();
}

export function closeUsernameEditor() {
  if (elements.usernameEditor) elements.usernameEditor.hidden = true;
  if (elements.editUsernameBtn) elements.editUsernameBtn.disabled = false;
}

export function getHandleFromPath() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  if (parts[0] !== "profile") return null;
  if (parts.length < 2) return null;
  const handle = decodeURIComponent(parts[1] || "").trim();
  return handle || null;
}
