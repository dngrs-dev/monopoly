const connectBtn = document.getElementById("connect");
const loginBtn = document.getElementById("login");
const logoutBtn = document.getElementById("logout");
const changeUsernameBtn = document.getElementById("change-username");
const currentUserEl = document.getElementById("current-user");
const errEl = document.getElementById("err");

let authed = false;
let currentUser = null;

function setError(text) {
  if (errEl) errEl.textContent = text || "";
}

function renderAuthState() {
  connectBtn.disabled = !authed;
  logoutBtn.disabled = !authed;
  changeUsernameBtn.disabled = !authed;
  currentUserEl.textContent = currentUser?.username || "(not signed in)";
}

async function checkAuth() {
  setError("");
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (!res.ok) {
      authed = false;
      currentUser = null;
      renderAuthState();
      return;
    }

    currentUser = await res.json().catch(() => null);
    authed = !!currentUser;
  } catch {
    authed = false;
    currentUser = null;
  }
  renderAuthState();
}

loginBtn.onclick = () => {
  window.location.href = "/login";
};

logoutBtn.onclick = async () => {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
    });
  } catch {}

  setError("");
  authed = false;
  currentUser = null;
  renderAuthState();
};

changeUsernameBtn.onclick = async () => {
  setError("");
  await checkAuth();
  if (!authed || !currentUser) return;

  const next = window.prompt(
    "Choose a new username (1-32 chars)",
    currentUser.username,
  );
  if (next === null) return;

  const username = next.trim();
  if (!username) {
    setError("Username is required");
    return;
  }

  const res = await fetch("/api/auth/username", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ username }),
  });

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    setError(data?.detail || "Could not update username");
    return;
  }

  currentUser = data?.user || currentUser;
  renderAuthState();
};

connectBtn.onclick = async () => {
  // Double-check so expired cookies don’t “fake enable” the button
  await checkAuth();
  if (!authed) return;

  // Fixed room for now (no extra UI requested)
  window.location.href = "/game?room=room1";
};

checkAuth();
