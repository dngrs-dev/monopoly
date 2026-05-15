homeButton = document.getElementById("home");
aboutButton = document.getElementById("about");
browseButton = document.getElementById("browse");
loginButton = document.getElementById("login");
signupButton = document.getElementById("signup");

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