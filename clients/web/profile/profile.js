const $ = (id) => document.getElementById(id);

const currentUserEl = $("current-user");
const currentUsernameEl = $("current-username");
const profileHandleEl = $("profile-handle");
const profileLinkEl = $("profile-link");
const usernameHistorySection = $("username-history-section");
const usernameHistoryEl = $("username-history");
const statsPlayedEl = $("stats-played");
const statsWinsEl = $("stats-wins");
const statusEl = $("status");
const errEl = $("err");
const avatarPreview = $("avatar-preview");
const avatarInput = $("avatar-input");
const avatarClear = $("avatar-clear");
const editUsernameBtn = $("edit-username");
const usernameEditor = $("username-editor");
const usernameInput = $("username-input");
const saveUsernameBtn = $("save-username");
const cancelUsernameBtn = $("cancel-username");
const backLobbyBtn = $("back-lobby");

const MAX_AVATAR_BYTES = 1024 * 1024; // 1 MB
const AVATAR_SIZE = 256;

let currentUser = null;
let profileData = null;
let viewingHandle = null;

function setError(text) {
	if (errEl) errEl.textContent = text || "";
}

function setStatus(text) {
	if (statusEl) statusEl.textContent = text || "";
}

function setAvatarPreview(src) {
	if (!avatarPreview) return;
	avatarPreview.src = src || "";
}

function setAvatarControlsEnabled(enabled) {
	if (avatarInput) avatarInput.disabled = !enabled;
	if (avatarClear) avatarClear.disabled = !enabled;
}

function setUsernameControlsEnabled(enabled) {
	if (editUsernameBtn) editUsernameBtn.disabled = !enabled;
	if (usernameInput) usernameInput.disabled = !enabled;
	if (saveUsernameBtn) saveUsernameBtn.disabled = !enabled;
	if (cancelUsernameBtn) cancelUsernameBtn.disabled = !enabled;
}

function openUsernameEditor() {
	if (usernameEditor) usernameEditor.hidden = false;
	if (editUsernameBtn) editUsernameBtn.disabled = true;
	if (usernameInput) usernameInput.focus();
}

function closeUsernameEditor() {
	if (usernameEditor) usernameEditor.hidden = true;
	if (editUsernameBtn) editUsernameBtn.disabled = false;
}

function getHandleFromPath() {
	const parts = window.location.pathname.split("/").filter(Boolean);
	if (parts[0] !== "profile") return null;
	if (parts.length < 2) return null;
	const handle = decodeURIComponent(parts[1] || "").trim();
	return handle || null;
}

async function fetchMe() {
	try {
		const res = await fetch("/api/auth/me", { credentials: "same-origin" });
		if (res.status === 401) return null;
		if (!res.ok) return null;
		return await res.json();
	} catch {
		return null;
	}
}

async function fetchProfile(handle) {
	const url = handle
		? `/api/profile/handle/${encodeURIComponent(handle)}`
		: "/api/profile/me";
	const res = await fetch(url, { credentials: "same-origin" });
	if (res.status === 401) return null;
	if (!res.ok) return null;
	return await res.json();
}

function loadAvatar(profile, isSelf) {
	if (!profile?.handle) return;
	const ts = Date.now();
	const url = isSelf
		? `/api/profile/avatar?ts=${ts}`
		: `/api/profile/avatar/${encodeURIComponent(profile.handle)}?ts=${ts}`;
	setAvatarPreview(url);
	if (avatarClear) avatarClear.disabled = !isSelf;
}

async function clearAvatar() {
	if (!profileData?.is_self) return;
	const res = await fetch("/api/profile/avatar", {
		method: "DELETE",
		credentials: "same-origin",
	});
	if (!res.ok) {
		setError("Could not clear avatar");
		return;
	}
	loadAvatar(profileData, true);
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
	canvas.width = AVATAR_SIZE;
	canvas.height = AVATAR_SIZE;
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("Canvas not available");

	ctx.drawImage(img, sx, sy, size, size, 0, 0, AVATAR_SIZE, AVATAR_SIZE);

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

async function saveAvatar(file) {
	if (!profileData?.is_self) return;
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

	if (blob.size > MAX_AVATAR_BYTES) {
		setError("Avatar must be 1MB or smaller");
		return;
	}

	const form = new FormData();
	form.append("file", blob, "avatar.png");

	const res = await fetch("/api/profile/avatar", {
		method: "POST",
		credentials: "same-origin",
		body: form,
	});

	if (!res.ok) {
		const data = await res.json().catch(() => null);
		setError(data?.detail || "Could not upload avatar");
		return;
	}

	const previewUrl = URL.createObjectURL(blob);
	setAvatarPreview(previewUrl);
	window.setTimeout(() => URL.revokeObjectURL(previewUrl), 1000);
	loadAvatar(profileData, true);
	setError("");
}

async function saveUsername() {
	if (!profileData?.is_self) return;
	const username = (usernameInput?.value || "").trim();
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

	if (data?.user) {
		currentUser = data.user;
	}
	await refreshProfile();
	closeUsernameEditor();
	setStatus("Username updated");
	setError("");
}

function renderHistory(history, show) {
	if (!usernameHistoryEl) return;
	usernameHistoryEl.innerHTML = "";

	if (!show) {
		usernameHistoryEl.textContent = "(hidden)";
		return;
	}

	if (!Array.isArray(history) || history.length === 0) {
		usernameHistoryEl.textContent = "(none)";
		return;
	}

	for (const item of history) {
		const li = document.createElement("li");
		li.textContent = item.username || "(unknown)";
		usernameHistoryEl.appendChild(li);
	}
}

function renderStats(stats) {
	if (statsPlayedEl)
		statsPlayedEl.textContent = String(stats?.games_played ?? 0);
	if (statsWinsEl) statsWinsEl.textContent = String(stats?.wins ?? 0);
}

function renderProfile() {
	if (!profileData) return;

	const isSelf = !!profileData.is_self;

	if (currentUsernameEl)
		currentUsernameEl.textContent = profileData.username || "(unknown)";
	if (profileHandleEl)
		profileHandleEl.textContent = profileData.handle || "(unknown)";
	if (profileLinkEl) {
		profileLinkEl.textContent = profileData.profile_link || "(unknown)";
		profileLinkEl.href = profileData.profile_link || "/profile";
	}

	renderStats(profileData.stats || { games_played: 0, wins: 0 });
	if (usernameHistorySection)
		usernameHistorySection.hidden = !isSelf;
	renderHistory(profileData.history, isSelf);

	setAvatarControlsEnabled(isSelf);
	setUsernameControlsEnabled(isSelf);
	if (usernameInput) usernameInput.value = profileData.username || "";
	closeUsernameEditor();
	loadAvatar(profileData, isSelf);
}

async function refreshProfile() {
	profileData = await fetchProfile(viewingHandle);
	if (!profileData) {
		setError("Profile not found or not accessible");
		return;
	}
	renderProfile();
}

if (avatarInput) {
	avatarInput.addEventListener("change", () => {
		setStatus("");
		setError("");
		const file = avatarInput.files?.[0];
		if (!file) return;
		saveAvatar(file);
		avatarInput.value = "";
	});
}

if (avatarClear) {
	avatarClear.addEventListener("click", () => {
		setStatus("");
		setError("");
		clearAvatar();
	});
}

if (editUsernameBtn) {
	editUsernameBtn.addEventListener("click", () => {
		if (!profileData?.is_self) return;
		setStatus("");
		setError("");
		if (usernameInput) usernameInput.value = profileData.username || "";
		openUsernameEditor();
	});
}

if (cancelUsernameBtn) {
	cancelUsernameBtn.addEventListener("click", () => {
		setStatus("");
		setError("");
		closeUsernameEditor();
	});
}

if (saveUsernameBtn) {
	saveUsernameBtn.addEventListener("click", () => {
		setStatus("");
		setError("");
		saveUsername();
	});
}

if (backLobbyBtn) {
	backLobbyBtn.addEventListener("click", () => {
		window.location.href = "/";
	});
}

(async function start() {
	setStatus("Loading...");
	viewingHandle = getHandleFromPath();
	currentUser = await fetchMe();

	if (!currentUser) {
		if (currentUserEl) currentUserEl.textContent = "(not signed in)";
		if (currentUsernameEl) currentUsernameEl.textContent = "(not signed in)";
		setStatus("");
		setError("Not authenticated. Go back and sign in.");
		setAvatarControlsEnabled(false);
		setUsernameControlsEnabled(false);
		return;
	}

	if (currentUserEl) currentUserEl.textContent = currentUser.username;
	setStatus("");
	await refreshProfile();
})();
