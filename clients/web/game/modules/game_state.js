import { state } from "./context.js";

export function isMyChoice(choice) {
  if (!choice) return false;
  if (!Number.isInteger(state.myPlayerId)) return false;
  return choice.player_id === state.myPlayerId;
}

export function getPlayerById(playerId) {
  const players = Array.isArray(state.lastSnapshot?.players)
    ? state.lastSnapshot.players
    : [];
  return players.find((p) => p?.id === playerId) || null;
}

export function getPlayerBalance(playerId) {
  const player = getPlayerById(playerId);
  return Number.isFinite(player?.balance) ? player.balance : 0;
}

export function getPlayerLabel(playerId) {
  return `Player ${playerId}`;
}

export function getOwnedProperties(playerId) {
  const tiles = Array.isArray(state.lastSnapshot?.tiles)
    ? state.lastSnapshot.tiles
    : [];
  const props = [];

  for (let pos = 0; pos < tiles.length; pos++) {
    const t = tiles[pos];
    if (!t || typeof t !== "object") continue;
    if (!("owner" in t)) continue;
    if (t.owner !== playerId) continue;
    props.push({ pos, name: t.name || `Property ${pos}` });
  }

  return props;
}
