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

async function loadSession() {
    const response = await fetch("/auth/session", {
        method: "GET",
        credentials: "include"
    });

    console.log("Session response:", response);
    if (response.ok) {
        const user = await response.json();
        guestActions.hidden = true;
        userActions.hidden = false;
        profileButton.addEventListener("click", () => {
            window.location.href = `/profile/${user.id}`;
        });
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
    // loadSession();
});

loadSession();