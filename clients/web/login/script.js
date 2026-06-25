const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const signupForm = document.getElementById("signup-form");
const signupError = document.getElementById("signup-error");

const loginContainer = document.querySelector(".login-container");
const signupContainer = document.querySelector(".signup-container");
const signupToggleContainer = document.querySelector(".signup-toggle-container");
const loginToggleContainer = document.querySelector(".login-toggle-container");

async function loadSession() {
    const session = await window.deedboundSession;

    if (session) {
        window.location.assign("/profile/"+session.profile_link);
    }
}

function showSignup() {
    loginContainer.hidden = true;
    signupToggleContainer.hidden = true;
    signupContainer.hidden = false;
    loginToggleContainer.hidden = false;
}

function showLogin() {
    signupContainer.hidden = true;
    loginToggleContainer.hidden = true;
    loginContainer.hidden = false;
    signupToggleContainer.hidden = false;
}

document.getElementById("toggle-signup").addEventListener("click", showSignup);
document.getElementById("toggle-login").addEventListener("click", showLogin);

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.hidden = true;

    const submitButton = loginForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = "Logging in…";

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
                email: loginForm.elements.email.value.trim(),
                password: loginForm.elements.password.value,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const detail = errorData.detail;
            const message = Array.isArray(detail)
                ? detail.map((item) => item.msg).join(" ")
                : detail;
            throw new Error(message || "Login failed. Check your details and try again.");
        }

        // If login is successful, redirect to the profile page
        // TODO: Redirect to the profile page, not reload the page.
        window.location.reload();
    } catch (error) {
        loginError.textContent = error.message || "Could not connect. Please try again.";
        loginError.hidden = false;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Login";
    }
});

signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    signupError.hidden = true;

    const password = signupForm.elements.password.value;
    const confirmPassword = signupForm.elements.confirmPassword.value;

    if (password !== confirmPassword) {
        signupError.textContent = "Passwords do not match.";
        signupError.hidden = false;
        signupForm.elements.confirmPassword.focus();
        return;
    }

    const submitButton = signupForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = "Creating account…";

    try {
        const response = await fetch("/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
                email: signupForm.elements.email.value.trim(),
                password,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const detail = errorData.detail;
            const message = Array.isArray(detail)
                ? detail.map((item) => item.msg).join(" ")
                : detail;
            throw new Error(message || "Could not create your account. Please try again.");
        }
        // If signup is successful, redirect to the profile page
        // TODO: Redirect to the profile page, not reload the page.
        window.location.reload();
    } catch (error) {
        signupError.textContent = error.message || "Could not connect. Please try again.";
        signupError.hidden = false;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Signup";
    }
});

loadSession();
