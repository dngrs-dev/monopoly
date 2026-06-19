async function loadHeader() {
    const [html, css] = await Promise.all([
        fetch("/static/partials/header.html").then((r) => r.text()),
        fetch("/static/partials/header.css").then((r) => r.text()),
    ]);

    const header = document.querySelector(".header");
    if (header) header.innerHTML = html;

    const styleId = "header-partial-style";
    if (!document.getElementById(styleId)) {
        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = css;
        document.head.appendChild(style);
    }

    initializeButtons();
    setupHeaderActions();
    showReconnect();
}

async function setupHeaderActions() {
    const guestActions = document.querySelector(".header-guest-actions");
    const userActions = document.querySelector(".header-user-actions");

    const user = window.monopolySession
        ? await window.monopolySession
        : await fetch("/auth/session", { credentials: "include" })
            .then((response) => response.ok ? response.json() : null)
            .catch(() => null);

    if (user) {
        if (guestActions) guestActions.hidden = true;
        if (userActions) userActions.hidden = false;
    } else {
        if (guestActions) guestActions.hidden = false;
        if (userActions) userActions.hidden = true;
    }
}

async function initializeButtons() {
    const loginButton = document.getElementById("header-login-button");
    const profileButton = document.getElementById("header-profile-button");
    const logoutButton = document.getElementById("header-logout-button");

    if (loginButton) loginButton.onclick = () => (window.location.href = "/login");
    if (profileButton) profileButton.onclick = () => (window.location.href = "/profile");

    if (logoutButton) {
        logoutButton.onclick = async () => {
            const response = await fetch("/auth/logout", {
                method: "POST",
                credentials: "include",
            });
            if (response.ok) {
                window.location.reload();
            } else {
                alert("Logout failed. Please try again.");
            }
        }
    };
}

async function showReconnect() {
    const reconnectEl = document.querySelector(".header-reconnect");
    const reconnectButton = document.getElementById("header-reconnect-button");
    
    const response = await fetch("/games/me", {
        method: "GET",
        credentials: "include",
    });

    if (!response.ok) {
        reconnectEl.hidden = true;
        return;
    }

    const data = await response.json();
    if (!data.active) {
        reconnectEl.hidden = true;
        return;
    }

    reconnectEl.hidden = false;
    reconnectButton.onclick = () => {
        window.location.href = `/games/${data.lobby_id}`;
    }
}

document.addEventListener("DOMContentLoaded", loadHeader);
