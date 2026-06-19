window.monopolySession = window.monopolySession || fetch("/auth/session", {
    method: "GET",
    credentials: "include",
})
    .then((response) => response.ok ? response.json() : null)
    .catch(() => null);
