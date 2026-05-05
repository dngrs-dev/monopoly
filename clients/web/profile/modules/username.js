import {
  elements,
  state,
  setError,
  setStatus,
  closeUsernameEditor,
} from "./context.js";
import { updateUsername } from "./api.js";
import { refreshProfile } from "./render.js";
import { getUsernameError } from "../../shared/validation.js";

export async function saveUsername() {
  if (!state.profileData?.is_self) return;
  const username = (elements.usernameInput?.value || "").trim();
  const error = getUsernameError(username);
  if (error) {
    setError(error);
    return;
  }

  const { ok, data } = await updateUsername(username);
  if (!ok) {
    setError(data?.detail || "Could not update username");
    return;
  }

  if (data?.user) {
    state.currentUser = data.user;
  }
  await refreshProfile();
  closeUsernameEditor();
  setStatus("Username updated");
  setError("");
}
