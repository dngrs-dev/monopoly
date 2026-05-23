const idElement = document.getElementById('id');
const displayNameElement = document.getElementById('display-name');
const avatarElement = document.getElementById('avatar');

const privateProfileElement = document.querySelector("[class='private-profile']");
const settingsButton = document.getElementById("settings");
const logoutButton = document.getElementById("logout");

async function loadProfile() {

    const slug = window.location.pathname.split('/').pop();

    const response = await fetch(`/profile/api/${encodeURIComponent(slug)}`, {
        credentials: 'include',
    });

    if (response.ok) {
        const user = await response.json();
        console.log(user);
        idElement.textContent = user.id;
        displayNameElement.textContent = user.display_name;
        avatarElement.src = user.avatar_url;
        current_user = await loadCurrentUser();
        if (current_user && current_user.id === user.id) {
            privateProfileElement.hidden = false;
        } else {
            privateProfileElement.hidden = true;
        }
    } else {
    }
}

async function loadCurrentUser() {
    const response = await fetch("/auth/session", {
        method: "GET",
        credentials: "include"
    });

    if (response.ok) {
        const user = await response.json();
        return user;
    } else {
        privateProfileElement.hidden = true;
    }
}

settingsButton.addEventListener("click", () => {
    window.location.href = "/settings";
});
logoutButton.addEventListener("click", async () => {
    await fetch("/auth/logout", {
        method: "POST",
        credentials: "include"
    });
    window.location.reload();
});

loadProfile();