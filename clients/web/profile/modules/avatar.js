import {
  constants,
  elements,
  state,
  setAvatarPreview,
  setError,
} from "./context.js";
import { deleteAvatar, uploadAvatar } from "./api.js";

export function loadAvatar(profile, isSelf) {
  if (!profile?.handle) return;
  const ts = Date.now();
  const url = isSelf
    ? `/api/profile/avatar?ts=${ts}`
    : `/api/profile/avatar/${encodeURIComponent(profile.handle)}?ts=${ts}`;
  setAvatarPreview(url);
  if (elements.avatarClear) elements.avatarClear.disabled = !isSelf;
}

export async function clearAvatar() {
  if (!state.profileData?.is_self) return;
  const ok = await deleteAvatar();
  if (!ok) {
    setError("Could not clear avatar");
    return;
  }
  loadAvatar(state.profileData, true);
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Image load failed"));
    };
    img.src = url;
  });
}

async function cropAvatar(file) {
  const img = await loadImageFromFile(file);
  const size = Math.min(img.width, img.height);
  const sx = Math.floor((img.width - size) / 2);
  const sy = Math.floor((img.height - size) / 2);

  const canvas = document.createElement("canvas");
  canvas.width = constants.AVATAR_SIZE;
  canvas.height = constants.AVATAR_SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas not available");

  ctx.drawImage(img, sx, sy, size, size, 0, 0, constants.AVATAR_SIZE, constants.AVATAR_SIZE);

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Avatar conversion failed"));
          return;
        }
        resolve(blob);
      },
      "image/png",
      0.92,
    );
  });
}

export async function saveAvatar(file) {
  if (!state.profileData?.is_self) return;
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    setError("Please select an image file");
    return;
  }

  let blob;
  try {
    blob = await cropAvatar(file);
  } catch {
    setError("Could not process avatar image");
    return;
  }

  if (blob.size > constants.MAX_AVATAR_BYTES) {
    setError("Avatar must be 1MB or smaller");
    return;
  }

  const { ok, data } = await uploadAvatar(blob);
  if (!ok) {
    setError(data?.detail || "Could not upload avatar");
    return;
  }

  const previewUrl = URL.createObjectURL(blob);
  setAvatarPreview(previewUrl);
  window.setTimeout(() => URL.revokeObjectURL(previewUrl), 1000);
  loadAvatar(state.profileData, true);
  setError("");
}
