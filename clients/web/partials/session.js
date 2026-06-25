window.deedboundSession = window.deedboundSession || fetch("/auth/session", {
    method: "GET",
    credentials: "include",
})
    .then((response) => response.ok ? response.json() : null)
    .catch(() => null);
