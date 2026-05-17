const homeButton = document.getElementById("home");
const aboutButton = document.getElementById("about");
const browseButton = document.getElementById("browse");
const loginButton = document.getElementById("login");
const signupButton = document.getElementById("signup");

const guestActions = document.querySelector("[is='guest-actions']");
const userActions = document.querySelector("[is='user-actions']");
const profileButton = document.getElementById("profile");
const logoutButton = document.getElementById("logout");

homeButton.addEventListener("click", () => {
    window.location.href = "/";
});

aboutButton.addEventListener("click", () => {
    window.location.href = "/about";
});

browseButton.addEventListener("click", () => {
    window.location.href = "/browse";
});

loginButton.addEventListener("click", () => {
    window.location.href = "/login";
});

signupButton.addEventListener("click", () => {
    window.location.href = "/signup";
});

profileButton.addEventListener("click", () => {
    window.location.href = `/profile`;
});

async function loadCurrentUser() {
    const response = await fetch("/auth/session", {
        method: "GET",
        credentials: "include"
    });

    if (response.ok) {
        guestActions.hidden = true;
        userActions.hidden = false;        
    } else {
        guestActions.hidden = false;
        userActions.hidden = true;
    }
}

logoutButton.addEventListener("click", async () => {
    await fetch("/auth/logout", {
        method: "POST",
        credentials: "include"
    });
    window.location.reload();
});

loadCurrentUser();