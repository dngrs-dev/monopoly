import { $, setText } from "../../shared/dom.js";

export const elements = {
  err: $("err"),
  registerHint: $("registerHint"),
  password: $("password"),
  submitBtn: $("submitBtn"),
  isRegister: $("isRegister"),
  loginForm: $("loginForm"),
  email: $("email"),
};

export function setError(text) {
  setText(elements.err, text || "");
}

export function updateMode() {
  const isRegister = !!elements.isRegister?.checked;

  if (elements.registerHint) elements.registerHint.hidden = !isRegister;
  if (elements.password)
    elements.password.autocomplete = isRegister
      ? "new-password"
      : "current-password";
  if (elements.submitBtn)
    elements.submitBtn.textContent = isRegister ? "Create account" : "Login";
}
