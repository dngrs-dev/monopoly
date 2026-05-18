// Menu and section handling
const menuItems = document.querySelectorAll(".menu-item");
const sections = document.querySelectorAll(".section > div");

function showSection(sectionName) {
    const tragetClass = `section-${sectionName}`;

    sections.forEach(section => {
        section.hidden = !section.classList.contains(tragetClass);
    });

    menuItems.forEach(item => {
        const hash = item.getAttribute("href");
        item.classList.toggle("active", hash === `#${sectionName}`);
    });
}

function onMenuClick(event) {
    event.preventDefault();
    const hash = event.currentTarget.getAttribute("href");
    const sectionName = hash.replace("#", "");
    history.replaceState(null, "", hash);
    showSection(sectionName);
}

menuItems.forEach(item => {
    item.addEventListener("click", onMenuClick);
});

const intialHash = window.location.hash.replace("#", "") || "general";
showSection(intialHash);



// Load user session
let currentUser = null;

async function loadSession() {
    const response = await fetch("/auth/session", {
        method: "GET",
        credentials: "include"
    });
    if (!response.ok) {
        window.location.href = "/login";
        return;
    }
    currentUser = await response.json();
    displayNameInput.value = currentUser.display_name;
    profileLinkInput.value = currentUser.profile_link;
}

loadSession();

// General settings handling

const displayNameInput = document.querySelector(".display-name-input");
const displayNameStatus = document.getElementById("display-name-status");
const displayNameSaveButton = document.getElementById("display-name-save");
const profileLinkInput = document.querySelector(".profile-link-input");
const profileLinkStatus = document.getElementById("profile-link-status");
const profileLinkSaveButton = document.getElementById("profile-link-save");

displayNameSaveButton.addEventListener("click", async () => {
    if (!currentUser) return;
    const newDisplayName = displayNameInput.value.trim();
    if (!newDisplayName) return;
    const response = await fetch("/settings/save", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ display_name: newDisplayName }),
    });
    if (response.ok) {
        currentUser.display_name = newDisplayName;
        checkStatus(displayNameInput, displayNameStatus, displayNameSaveButton);
    } else {
        displayNameStatus.textContent = "Failed to save display name. Please try again.";
        displayNameStatus.dataset.state = "bad";
    }
});

profileLinkSaveButton.addEventListener("click", async () => {
    if (!currentUser) return;
    const newProfileLink = profileLinkInput.value.trim();
    if (!newProfileLink) return;
    const response = await fetch("/settings/save", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ profile_link: newProfileLink }),
    });
    if (response.ok) {
        currentUser.profile_link = newProfileLink;
        checkStatus(profileLinkInput, profileLinkStatus, profileLinkSaveButton);
    } else {
        profileLinkStatus.textContent = "Failed to save profile link. Please try again.";
        profileLinkStatus.dataset.state = "bad";
    }
});

let checkTimer = null;
let activeController = null;

function setStatus(statusElement, text, state) {
    statusElement.textContent = text;
    statusElement.dataset.state = state; // "ok", "bad", "loading"
}

async function checkStatus(inputElement, statusElement, buttonElement) {
    if (!currentUser) return;
    buttonElement.disabled = true;
    buttonElement.hidden = true;

    const value = inputElement.value.trim();
    if (!value) {
        setStatus(statusElement, "", "");
        return;
    }

    if (activeController) activeController.abort();
    activeController = new AbortController();

    setStatus(statusElement, "Checking...", "loading");

    const response = await fetch(`/settings/check?${inputElement === displayNameInput ? "display_name" : "profile_link"}=${encodeURIComponent(value)}`, {
        method: "GET",
        signal: activeController.signal
    }).catch(() => null);
    console.log(response);

    if (!response) return;

    if (inputElement === displayNameInput) {
        if (currentUser.display_name === value) {
            setStatus(statusElement, "Current display name", "ok");
            return;
        }
    }
    if (inputElement === profileLinkInput) {
        if (currentUser.profile_link === value) {
            setStatus(statusElement, "Current profile link", "ok");
            return;
        }
    }

    const data = await response.json().catch(() => ({}));
    console.log(data);
    if (data.available) {
        setStatus(statusElement, "Available", "ok");
        buttonElement.disabled = false;
        buttonElement.hidden = false;
    } else {
        setStatus(statusElement, "Already taken", "bad");
    }
}

function scheduleCheck(inputElement, statusElement, buttonElement) {
    clearTimeout(checkTimer);
    checkTimer = setTimeout(() => checkStatus(inputElement, statusElement, buttonElement), 500);
}

displayNameInput.addEventListener("input", () => scheduleCheck(displayNameInput, displayNameStatus, displayNameSaveButton));
profileLinkInput.addEventListener("input", () => scheduleCheck(profileLinkInput, profileLinkStatus, profileLinkSaveButton));
displayNameInput.addEventListener("blur", () => checkStatus(displayNameInput, displayNameStatus, displayNameSaveButton));
profileLinkInput.addEventListener("blur", () => checkStatus(profileLinkInput, profileLinkStatus, profileLinkSaveButton));



// Avatar change handling

const avatarImage = document.getElementById("avatar-image");
const avatarFileInput = document.getElementById("avatar-file-input");
const avatarStatus = document.getElementById("avatar-status");

avatarFileInput.addEventListener("change", async () => {
    const file = avatarFileInput.files[0];
    if (!file) return;

    // Preview
    const previewUrl = URL.createObjectURL(file);
    avatarImage.src = previewUrl;

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/settings/avatar", {
        method: "POST",
        credentials: "include",
        body: formData
    });

    if (!response.ok) {
        avatarStatus.textContent = "Failed to upload avatar. Please try again.";
        avatarStatus.dataset.state = "bad";
        return;
    }

    const data = await response.json();
    avatarImage.src = data.avatar_url;
    avatarStatus.textContent = "Avatar updated successfully!";
    avatarStatus.dataset.state = "ok";

    URL.revokeObjectURL(previewUrl);
});