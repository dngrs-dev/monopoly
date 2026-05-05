export const $ = (id) => document.getElementById(id);

export function setText(el, text) {
  if (!el) return;
  if (text === null || text === undefined) {
    el.textContent = "";
    return;
  }
  el.textContent = String(text);
}
