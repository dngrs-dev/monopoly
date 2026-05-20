async function loadFooter() {
    const [html, css] = await Promise.all([
        fetch("/static/partials/footer.html").then((r) => r.text()),
        fetch("/static/partials/footer.css").then((r) => r.text()),
    ]);

    const footer = document.querySelector(".footer");
    if (footer) footer.innerHTML = html;

    const styleId = "footer-partial-style";
    if (!document.getElementById(styleId)) {
        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = css;
        document.head.appendChild(style);
    }
}

document.addEventListener("DOMContentLoaded", loadFooter);