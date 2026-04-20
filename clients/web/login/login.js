const $ = (id) => document.getElementById(id);

function setError(text) {
  $("err").textContent = text || "";
}

$("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  setError("");

  const username = $("username").value.trim();
  if (!username) {
    setError("Username is required");
    return;
  }

  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ username }),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    setError(data?.detail || "Login failed");
    return;
  }

  // This redirect is user-triggered (after submit), not automatic on open.
  window.location.href = "/";
});
