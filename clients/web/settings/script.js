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

async function loadSession() {
    const response = await fetch("/auth/session", {
        method: "GET",
        credentials: "include"
    });

    if (response.ok) {
        const user = await response.json();
        console.log("User data:", user);
    } else {
        console.log("No active session found.");
        window.location.href = "/login";
    }
}

loadSession();