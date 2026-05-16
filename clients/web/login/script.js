const form = document.getElementById('login-form');
const errorElement = document.getElementById('login-error');

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorElement.hidden = true;

    const payload = {
        email: form.email.value.trim(),
        password: form.password.value
    };

    const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        errorElement.textContent = errorData.detail || 'Login failed. Please try again.';
        errorElement.hidden = false;
        return;
    }

    window.location.href = '/';
});