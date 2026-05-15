loginButton = document.getElementById("login");
signupButton = document.getElementById("signup");

loginButton.addEventListener("click", () => {
    window.location.href = "/login";
});

signupButton.addEventListener("click", () => {
    window.location.href = "/signup";
});