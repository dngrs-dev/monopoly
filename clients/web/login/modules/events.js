import { elements, setError, updateMode } from "./context.js";
import { submitLogin } from "./api.js";
import {
  getEmailError,
  getPasswordError,
} from "../../shared/validation.js";

function validate(email, password) {
  return getEmailError(email) || getPasswordError(password) || "";
}

export function wireEvents() {
  if (elements.isRegister) {
    elements.isRegister.addEventListener("change", () => {
      setError("");
      updateMode();
    });
  }

  if (elements.loginForm) {
    elements.loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError("");

      const email = (elements.email?.value || "").trim();
      const password = elements.password?.value || "";
      const isRegister = !!elements.isRegister?.checked;

      const error = validate(email, password);
      if (error) {
        setError(error);
        return;
      }

      const { ok, data } = await submitLogin({ email, password, isRegister });
      if (!ok) {
        const fallback = isRegister ? "Registration failed" : "Login failed";
        setError(data?.detail || fallback);
        return;
      }

      window.location.href = "/";
    });
  }
}
