const connectBtn = document.getElementById("connect");
const loginBtn = document.getElementById("login");
const logoutBtn = document.getElementById("logout");

let authed = false;

async function checkAuth() {
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    authed = res.ok;
  } catch {
    authed = false;
  }
  connectBtn.disabled = !authed;
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
  authed = false;
  connectBtn.disabled = true;
};

connectBtn.onclick = async () => {
  // Double-check so expired cookies don’t “fake enable” the button
  await checkAuth();
  if (!authed) return;

  // Fixed room for now (no extra UI requested)
  window.location.href = "/game?room=room1";
};

checkAuth();
