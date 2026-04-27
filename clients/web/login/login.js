const $ = (id) => document.getElementById(id);

function setError(text) {
  $("err").textContent = text || "";
}

function updateMode() {
  const isRegister = $("isRegister").checked;

  const registerHint = $("registerHint");
  const password = $("password");
  const submitBtn = $("submitBtn");

  registerHint.hidden = !isRegister;

  password.autocomplete = isRegister ? "new-password" : "current-password";
  submitBtn.textContent = isRegister ? "Create account" : "Login";
}

$("isRegister").addEventListener("change", () => {
  setError("");
  updateMode();
});

updateMode();

$("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  setError("");

  const email = $("email").value.trim();
  const password = $("password").value;
  const isRegister = $("isRegister").checked;

  if (!email) {
    setError("Email is required");
    return;
  }
  if (!email.includes("@")) {
    setError("Email looks invalid");
    return;
  }
  if (!password) {
    setError("Password is required");
    return;
  }

  const body = { email, password };

  const endpoint = isRegister ? "/api/auth/register" : "/api/auth/login";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const fallback = isRegister ? "Registration failed" : "Login failed";
    setError(data?.detail || fallback);
    return;
  }

  // This redirect is user-triggered (after submit), not automatic on open.
  window.location.href = "/";
});
