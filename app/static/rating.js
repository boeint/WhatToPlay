// 1-5 star rating as radio buttons (keyboard-friendly), plus "devices you've used"
// suggestions. Used by the detail panel and the "Finished!" window.

// prefix keeps ids unique when two ratings are on the page at once.
export function starsField(prefix, value) {
  // Highest first in the HTML, shown left to right by CSS (row-reverse), so a
  // checked or hovered star can light up the lower ones that follow it.
  const stars = [5, 4, 3, 2, 1].map((n) => `
    <input type="radio" name="rating" id="${prefix}-star-${n}" value="${n}" ${value === n ? "checked" : ""}>
    <label for="${prefix}-star-${n}" title="${n} star${n === 1 ? "" : "s"}">★</label>`).join("");
  return `<span class="stars" role="radiogroup" aria-label="Rating">${stars}</span>
    <button type="button" class="lnkbtn" data-clear-rating>clear</button>`;
}

export function readStars(container) {
  const checked = container.querySelector('[name="rating"]:checked');
  return checked ? Number(checked.value) : null;
}

// "clear" buttons inside any rating (panel or dialog).
document.addEventListener("click", (event) => {
  const clear = event.target.closest("[data-clear-rating]");
  if (!clear) return;
  clear.parentElement.querySelectorAll('[name="rating"]').forEach((input) => { input.checked = false; });
  clear.parentElement.dispatchEvent(new Event("change", { bubbles: true }));
});

// Every device already used, for the "Played on" suggestions.
export function knownDevices(franchises) {
  const devices = new Set(franchises.flatMap((f) => f.games.map((g) => g.device)).filter(Boolean));
  return [...devices].sort((a, b) => a.localeCompare(b));
}

export function devicesDatalist(id, devices) {
  const esc = (v) => String(v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  return `<datalist id="${id}">${devices.map((d) => `<option value="${esc(d)}">`).join("")}</datalist>`;
}
