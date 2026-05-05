export function clampLobbyLimit(value) {
  if (!Number.isFinite(value)) return 4;
  if (value < 1) return 1;
  if (value > 8) return 8;
  return value;
}

export function formatCountdown(secondsLeft) {
  const safeSeconds = Math.max(0, Math.floor(secondsLeft));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
