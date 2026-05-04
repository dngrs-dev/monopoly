const $ = (id) => document.getElementById(id);

const currentUserEl = $("current-user");
const currentUsernameEl = $("current-username");
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

function loadAvatar() {
	if (!currentUser) return;
	const ts = Date.now();
	setAvatarPreview(`/api/profile/avatar?ts=${ts}`);
	if (avatarClear) avatarClear.disabled = false;
}

async function clearAvatar() {
	if (!currentUser) return;
	const res = await fetch("/api/profile/avatar", {
		method: "DELETE",
		credentials: "same-origin",
	});
	if (!res.ok) {
		setError("Could not clear avatar");
		return;
	}
	loadAvatar();
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
	if (!currentUser) return;
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
	loadAvatar();
	setError("");
}

async function saveUsername() {
	if (!currentUser) return;
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

	currentUser = data?.user || currentUser;
	if (currentUserEl) currentUserEl.textContent = currentUser.username;
	if (currentUsernameEl) currentUsernameEl.textContent = currentUser.username;
	closeUsernameEditor();
	setStatus("Username updated");
	setError("");
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
		if (!currentUser) return;
		setStatus("");
		setError("");
		if (usernameInput) usernameInput.value = currentUser.username;
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
	if (currentUsernameEl) currentUsernameEl.textContent = currentUser.username;
	if (usernameInput) usernameInput.value = currentUser.username;
	setStatus("");
	setAvatarControlsEnabled(true);
	setUsernameControlsEnabled(true);
	closeUsernameEditor();
	loadAvatar();
})();
