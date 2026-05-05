export async function fetchMe() {
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (res.status === 401) return null;
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchProfile(handle) {
  const url = handle
    ? `/api/profile/handle/${encodeURIComponent(handle)}`
    : "/api/profile/me";
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    if (res.status === 401) return null;
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function updateUsername(username) {
  try {
    const res = await fetch("/api/auth/username", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ username }),
    });
    const data = await res.json().catch(() => null);
    return { ok: res.ok, data };
  } catch {
    return { ok: false, data: null };
  }
}

export async function uploadAvatar(blob) {
  const form = new FormData();
  form.append("file", blob, "avatar.png");

  try {
    const res = await fetch("/api/profile/avatar", {
      method: "POST",
      credentials: "same-origin",
      body: form,
    });
    const data = await res.json().catch(() => null);
    return { ok: res.ok, data };
  } catch {
    return { ok: false, data: null };
  }
}

export async function deleteAvatar() {
  try {
    const res = await fetch("/api/profile/avatar", {
      method: "DELETE",
      credentials: "same-origin",
    });
    return res.ok;
  } catch {
    return false;
  }
}
