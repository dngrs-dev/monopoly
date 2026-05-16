const form = document.getElementById("signup-form");
const errorElement = document.getElementById("signup-error");

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorElement.hidden = true;

    const payload = {
        email: form.email.value.trim(),
        password: form.password.value,
    };

    const response = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData.detail;
        errorElement.textContent = Array.isArray(detail)
            ? detail.map((d) => d.msg).join(", ")
            : (detail || "Sign up failed. Please try again.");
        errorElement.hidden = false;
        return;
    }

    window.location.href = "/";
});