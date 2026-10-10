// "What to play next": suggest the next game (in play order) of a few random
// franchises. A franchise takes part only if its next game (the first one not
// finished or skipped) is released (not TBA or upcoming) and not already being played.

const overlay = document.getElementById("picker");
const PICKS = 3;      // suggestions shown at once (each from a different franchise)

let current = null;   // { franchises, onPlaying, onOpen }
let picks = [];       // [{ franchise, game }, ...]
let scope = "all";    // "all" or a franchise id

// Filters, remembered on this device.
const FILTERS_KEY = "whattoplay.picker";
const LENGTHS = {                       // [min, max) in hours
  short: [1, 10],
  medium: [10, 30],
  long: [30, Infinity],
};
let filters = { playOn: "any", length: "any", series: "either" };
try {
  Object.assign(filters, JSON.parse(localStorage.getItem(FILTERS_KEY) || "null"));
} catch { /* storage unavailable: defaults */ }

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const nextGame = (f) => f.games.find((g) => g.status !== "finished" && g.status !== "skip") || null;

// Not out yet: TBA, or dated after the current month (dates are month + year, so a
// game released "this month" counts as released; a year-only date from that year).
function isUnreleased(game) {
  if (game.release_tba) return true;
  if (!game.release_year) return false;
  const now = new Date();
  const thisMonth = now.getFullYear() * 12 + now.getMonth() + 1;
  const released = game.release_year * 12 + (game.release_month || 1);
  return released > thisMonth;
}

// Every franchise whose next game can be suggested, with that game (before the filters).
function candidates() {
  return current.franchises
    .map((franchise) => ({ franchise, game: nextGame(franchise) }))
    .filter(({ game }) => game && !isUnreleased(game) && game.status !== "playing");
}

const started = (franchise) => franchise.games.some((g) => g.status === "finished");

function matchesFilters({ franchise, game }) {
  if (filters.playOn !== "any" && game.play_on !== filters.playOn) return false;
  if (filters.length !== "any") {
    const [min, max] = LENGTHS[filters.length];
    if (game.length_hours == null || game.length_hours < min || game.length_hours >= max) return false;
  }
  if (filters.series === "continue" && !started(franchise)) return false;
  if (filters.series === "new" && started(franchise)) return false;
  return true;
}

// A random order (Fisher–Yates shuffle: every order equally likely).
function shuffled(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function roll() {
  const all = candidates();
  const pool = (scope === "all" ? all : all.filter((c) => c.franchise.id === scope)).filter(matchesFilters);
  // Re-rolling prefers games not just shown; it reuses some only when there aren't enough others.
  const shown = new Set(picks.map((p) => p.game.id));
  const fresh = shuffled(pool.filter((c) => !shown.has(c.game.id)));
  const again = shuffled(pool.filter((c) => shown.has(c.game.id)));
  picks = [...fresh, ...again].slice(0, PICKS);
}

function renderPick({ franchise, game: g }, index) {
  const where = g.play_on ? `Play on <b>${esc(g.play_on)}</b>` : esc(g.platforms.join(" · ") || "platform: tbd");
  return `<div class="pick-card">
      <div class="roll-fr">${esc(franchise.name)}</div>
      <div class="pick-game"><a href="${esc(g.backloggd_link)}" target="_blank" rel="noopener" title="Open on Backloggd">${esc(g.title)}</a></div>
      <div class="roll-plat">${where}${g.released ? ` — ${esc(g.released)}` : ""}${g.length_hours ? ` · ~${g.length_hours} h` : ""}</div>
      ${g.notes ? `<div class="roll-note">“${esc(g.notes)}”</div>` : ""}
      <div class="pick-actions">
        <button type="button" data-picker="playing" data-index="${index}">Set as Playing</button>
        <button type="button" class="btn-ghost" data-picker="open" data-index="${index}">Open details</button>
      </div>
    </div>`;
}

function render() {
  const all = candidates();
  const options = [...all].sort((a, b) => a.franchise.name.localeCompare(b.franchise.name))
    .map(({ franchise }) => `<option value="${franchise.id}" ${scope === franchise.id ? "selected" : ""}>${esc(franchise.name)}</option>`)
    .join("");
  const playOns = [...new Set(all.map((c) => c.game.play_on).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b));
  if (filters.playOn !== "any" && !playOns.includes(filters.playOn)) playOns.push(filters.playOn);
  const option = (value, label, chosen) =>
    `<option value="${esc(value)}" ${chosen === value ? "selected" : ""}>${esc(label)}</option>`;
  const filterRow = `<div class="picker-filters">
      <label>Play on <select data-filter="playOn">${option("any", "Any", filters.playOn)}${
        playOns.map((p) => option(p, p, filters.playOn)).join("")}</select></label>
      <label>Length <select data-filter="length">${option("any", "Any", filters.length)}${
        option("short", "Short (under 10 h)", filters.length)}${option("medium", "Medium (10–30 h)", filters.length)}${
        option("long", "Long (30 h+)", filters.length)}</select></label>
      <label>Series <select data-filter="series">${option("either", "Either", filters.series)}${
        option("continue", "Continue one I've started", filters.series)}${
        option("new", "Start something new", filters.series)}</select></label>
    </div>`;
  const filtering = filters.playOn !== "any" || filters.length !== "any" || filters.series !== "either";
  const matching = all.filter(matchesFilters).length;
  const body = picks.length
    ? `<div class="pick-list">${picks.map(renderPick).join("")}</div>`
    : filtering
      ? `<div class="roll-card"><div class="roll-game">Nothing matches</div>
          <div class="roll-plat">No game fits these filters${scope === "all" ? "" : " in this franchise"}.
            <button type="button" class="lnkbtn" data-picker="reset-filters">Reset filters</button></div></div>`
      : `<div class="roll-card"><div class="roll-game">🎉 All caught up!</div>
          <div class="roll-plat">Nothing to suggest${scope === "all" ? "" : " in this franchise"}.</div></div>`;
  overlay.innerHTML = `<div class="modal picker-modal" role="dialog" aria-modal="true" aria-label="What to play next">
      <div class="filter-roll">Pick from:
        <select data-picker="scope" aria-label="Pick from"><option value="all">any franchise</option>${options}</select>
      </div>
      ${filterRow}
      ${body}
      <div class="roll-hint">${filtering ? `${matching} of ` : ""}${all.length} franchise${all.length === 1 ? "" : "s"} in the draw${
        filtering ? " match the filters" : ""}. Unreleased (TBA or upcoming) and already-playing games are left out.${
        filters.length !== "any" ? " Games without a length only appear with Length: Any." : ""}</div>
      <div class="roll-actions">
        <button type="button" class="btn-roll" data-picker="roll">🎲 Re-roll</button>
        <button type="button" class="btn-ghost" data-picker="close">Close</button>
      </div>
    </div>`;
}

export function openPicker(options) {
  current = options;
  if (scope !== "all" && !current.franchises.some((f) => f.id === scope)) scope = "all";
  picks = [];
  roll();
  render();
  overlay.classList.add("on");
  overlay.querySelector('[data-picker="roll"]').focus();
}

function close() {
  overlay.classList.remove("on");
}

overlay.addEventListener("click", async (event) => {
  if (event.target === overlay) return close();   // click outside the box
  const button = event.target.closest("[data-picker]");
  const action = button?.dataset.picker;
  const chosen = picks[Number(button?.dataset.index)];
  if (action === "roll") { roll(); render(); }
  else if (action === "reset-filters") { setFilters({ playOn: "any", length: "any", series: "either" }); }
  else if (action === "close") close();
  else if (action === "open") { close(); current.onOpen(chosen.game, chosen.franchise); }
  else if (action === "playing") {
    close();
    await current.onPlaying(chosen.game, chosen.franchise);
  }
});

function setFilters(changes) {
  Object.assign(filters, changes);
  try { localStorage.setItem(FILTERS_KEY, JSON.stringify(filters)); } catch { /* private mode */ }
  picks = [];
  roll();
  render();
}

overlay.addEventListener("change", (event) => {
  const filter = event.target.dataset.filter;
  if (filter) return setFilters({ [filter]: event.target.value });
  if (event.target.dataset.picker !== "scope") return;
  scope = event.target.value === "all" ? "all" : Number(event.target.value);
  picks = [];
  roll();
  render();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && overlay.classList.contains("on")) close();
});
