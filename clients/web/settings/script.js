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


const displayNameInput = document.querySelector(".display-name-input");
const displayNameStatus = document.getElementById("display-name-status");
const profileLinkInput = document.querySelector(".profile-link-input");
const profileLinkStatus = document.getElementById("profile-link-status");

let checkTimer = null;
let activeController = null;

function setStatus(statusElement, text, state) {
    statusElement.textContent = text;
    statusElement.dataset.state = state; // "ok", "bad", "loading"
}

async function checkStatus(inputElement, statusElement) {
    if (!currentUser) return;

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
    } else {
        setStatus(statusElement, "Already taken", "bad");
    }
}

function scheduleCheck(inputElement, statusElement) {
    clearTimeout(checkTimer);
    checkTimer = setTimeout(() => checkStatus(inputElement, statusElement), 500);
}

displayNameInput.addEventListener("input", () => scheduleCheck(displayNameInput, displayNameStatus));
profileLinkInput.addEventListener("input", () => scheduleCheck(profileLinkInput, profileLinkStatus));

