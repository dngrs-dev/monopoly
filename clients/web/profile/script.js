const avatarElement = document.getElementById('avatar');
const displayNameElement = document.getElementById('display-name');

async function loadProfile() {

    const slug = window.location.pathname.split('/').pop();

    const response = await fetch(`/profile/api/${encodeURIComponent(slug)}`, {
        credentials: 'include',
    });

    if (response.ok) {
        const user = await response.json();
        console.log(user);
        avatarElement.src = user.avatar_url;
        displayNameElement.textContent = user.display_name;
    } else {
    }
}

loadProfile();