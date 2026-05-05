import { $, setText } from "../shared/dom.js";

export const elements = {
  createLobbyBtn: $("create-lobby"),
  lobbyLimitInput: $("lobby-limit"),
  lobbyVisibilitySelect: $("lobby-visibility"),
  lobbyListEl: $("lobby-list"),
  myLobbySection: $("my-lobby"),
  myLobbyIdEl: $("my-lobby-id"),
  myLobbyOwnerEl: $("my-lobby-owner"),
  myLobbyVisibilityEl: $("my-lobby-visibility"),
  myLobbyInviteEl: $("my-lobby-invite"),
  myLobbyLimitEl: $("my-lobby-limit"),
  myLobbyMembersEl: $("my-lobby-members"),
  ownerCountdownRow: $("owner-countdown-row"),
  ownerCountdownEl: $("owner-countdown"),
  startLobbyBtn: $("start-lobby"),
  leaveLobbyBtn: $("leave-lobby"),
  inviteCodeInput: $("invite-code"),
  joinPrivateBtn: $("join-private"),
  statusEl: $("ws-status"),
  loginBtn: $("login"),
  logoutBtn: $("logout"),
  profileBtn: $("profile"),
  currentUserEl: $("current-user"),
  errEl: $("err"),
};

export const state = {
  ws: null,
  lobbyList: [],
  currentLobby: null,
  authed: false,
  currentUser: null,
  countdownTimer: null,
  countdownExpiresAt: null,
};

export function setError(text) {
  setText(elements.errEl, text || "");
}

export function setStatus(text) {
  setText(elements.statusEl, text || "");
}

export function isWsReady() {
  return state.ws && state.ws.readyState === WebSocket.OPEN;
}
