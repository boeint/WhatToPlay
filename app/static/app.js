// WhatToPlay page: rendering and user interaction.
// All data comes from the backend through api.js.
import { api } from "./api.js";
import { openGamePanel } from "./panel.js";

// ---------- state ----------
let franchises = [];          // from GET /api/franchises, in custom order
let platforms = [];           // from GET /api/platforms, in display order
const expanded = new Set();   // franchise ids; collapsed by default on every load

// Column widths are a per-device display preference, kept in this browser.
const COLUMN_DEFAULTS = { released: 92, platform: 200, playon: 110, status: 110, notes: 200, links: 80 };
const COLUMNS = Object.keys(COLUMN_DEFAULTS);
let columnWidths = { ...COLUMN_DEFAULTS };
try {
  Object.assign(columnWidths, JSON.parse(localStorage.getItem("whattoplay.cols") || "null"));
} catch { /* ignore broken saved value */ }

const STATUSES = [["unplayed", "Unplayed"], ["playing", "Playing"], ["finished", "Finished"], ["skip", "Skip"]];

// ---------- helpers ----------
const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const isOpenGame = (g) => g.status !== "finished" && g.status !== "skip";
const remaining = (f) => f.games.filter(isOpenGame).length;
const onDeck = (f) => f.games.find(isOpenGame) || null;   // first game not finished/skipped

const findFranchise = (id) => franchises.find((f) => f.id === id);
function findGame(id) {
  for (const f of franchises) {
    const g = f.games.find((x) => x.id === id);
    if (g) return { franchise: f, game: g };
  }
  return {};
}

function colgroup() {
  const cols = COLUMNS.map((k) => `<col data-col="${k}" style="width:${columnWidths[k]}px">`).join("");
  return `<colgroup><col>${cols}<col style="width:34px"><col style="width:34px"></colgroup>`;
}

// ---------- rendering ----------
function renderGame(g) {
  const chips = g.platforms.length
    ? g.platforms.map((p) => `<span class="chip">${esc(p)}</span>`).join("")
    : `<span class="ph">+ platform</span>`;
  const statusOptions = STATUSES.map(([value, label]) =>
    `<option value="${value}" ${g.status === value ? "selected" : ""}>${label}</option>`).join("");
  const playOnOptions = `<option value="">—</option>` + g.platforms.map((p) =>
    `<option ${g.play_on === p ? "selected" : ""}>${esc(p)}</option>`).join("");
  const links = g.links.map((l) =>
    `<a href="${esc(l.url)}" target="_blank" rel="noopener" title="${esc(l.url)}">${esc(l.label)}</a>`).join("");
  return `<tr class="${g.status}" data-game="${g.id}">
    <td class="t-title"><div class="title-wrap"><span class="gmark">▹</span>
      <input data-field="title" value="${esc(g.title)}" aria-label="Title">
      <a class="bl" href="${esc(g.backloggd_link)}" target="_blank" rel="noopener" title="Open on Backloggd"><img src="https://backloggd.com/favicon.ico" alt="Backloggd"></a>
      <button class="open-panel" data-action="open-panel" title="All details">✎</button>
    </div></td>
    <td class="t-rel" data-action="open-panel" title="Edit release date">${esc(g.released)}</td>
    <td><div class="plat-cell" data-action="open-panel" title="Edit platforms">${chips}</div></td>
    <td class="t-playon"><select data-field="play_on" aria-label="Play on" ${g.platforms.length ? "" : "disabled"}>${playOnOptions}</select></td>
    <td><select data-field="status" class="status ${g.status}" aria-label="Status">${statusOptions}</select></td>
    <td class="t-notes"><input data-field="notes" value="${esc(g.notes)}" aria-label="Notes"></td>
    <td class="t-links">${links}<button class="lnkbtn">＋</button></td>
    <td><div class="ord"><button title="Up">▲</button><button title="Down">▼</button></div></td>
    <td><button class="del" title="Delete game">×</button></td>
  </tr>`;
}

// The part of a franchise header that depends on its games' statuses.
function renderSummary(f) {
  const deck = onDeck(f);
  const total = f.games.length;
  return `<span class="fr-prog">${total - remaining(f)}/${total} done</span>` + (deck
    ? `<span class="ondeck" title="Next up">▶ ${esc(deck.title)}</span>`
    : `<span class="fr-prog" style="color:var(--done)">✓ complete</span>`);
}

function renderFranchise(f) {
  const open = expanded.has(f.id);
  return `<div class="fr ${open ? "open" : ""}" data-franchise="${f.id}">
    <div class="fr-head" data-action="toggle">
      <span class="caret">▶</span>
      <input class="fr-title" data-field="name" value="${esc(f.name)}" aria-label="Franchise name">
      <span class="fr-summary">${renderSummary(f)}</span>
    </div>
    <div class="fr-body">
      <div class="fr-notes"><span class="lbl">Notes</span><textarea data-field="notes" aria-label="Franchise notes">${esc(f.notes)}</textarea></div>
      <div class="games-frame"><table>${colgroup()}<thead><tr>
        <th>Title</th>
        <th>Released<span class="rz" data-col="released"></span></th>
        <th>Platform<span class="rz" data-col="platform"></span></th>
        <th>Play on<span class="rz" data-col="playon"></span></th>
        <th>Status<span class="rz" data-col="status"></span></th>
        <th>Notes<span class="rz" data-col="notes"></span></th>
        <th>Links<span class="rz" data-col="links"></span></th>
        <th></th><th></th>
      </tr></thead><tbody>${f.games.map(renderGame).join("")}</tbody></table></div>
    </div>
  </div>`;
}

function render() {
  // Default sort: A–Z by name, literal first word ("The" counts).
  const list = [...franchises].sort((a, b) => a.name.localeCompare(b.name));
  $("app").innerHTML = list.map(renderFranchise).join("") || `<div class="empty">No franchises yet.</div>`;
  renderStats();
}

function renderStats() {
  const games = franchises.flatMap((f) => f.games);
  const count = (status) => games.filter((g) => g.status === status).length;
  $("stats").innerHTML =
    `<span>📚 <b>${franchises.length}</b> franchises</span><span>🎮 <b>${games.length}</b> games</span>` +
    `<span>✅ <b>${count("finished")}</b> done</span><span>▶ <b>${count("playing")}</b> playing</span>` +
    `<span>⏳ <b>${games.filter(isOpenGame).length}</b> left</span>`;
}

// Redraw just one game row and its franchise's summary (keeps focus elsewhere intact).
function refreshGame(franchise, game) {
  const row = document.querySelector(`tr[data-game="${game.id}"]`);
  if (row) row.outerHTML = renderGame(game);
  refreshSummary(franchise);
}

function refreshSummary(franchise) {
  const summary = document.querySelector(`[data-franchise="${franchise.id}"] .fr-summary`);
  if (summary) summary.innerHTML = renderSummary(franchise);
  renderStats();
}

// ---------- save feedback ----------
let fadeTimer;
function saveState(text, cls = "") {
  const el = $("save-state");
  clearTimeout(fadeTimer);
  el.className = `save-state ${cls}`;
  el.textContent = text;
  if (cls === "saved") fadeTimer = setTimeout(() => el.classList.add("fade"), 1500);
}

function showProblem(message) {
  const box = $("problem");
  box.innerHTML = `<span>⚠ ${esc(message)}</span><button data-action="dismiss">Dismiss</button>`;
  box.hidden = false;
}

// Run a save; on failure, explain and reload the real data from the server.
async function save(work) {
  saveState("Saving…");
  try {
    await work();
    saveState("Saved ✓", "saved");
  } catch (err) {
    saveState("");
    showProblem(`Not saved: ${err.message}`);
    await load();
  }
}

// ---------- edits ----------
async function editGame(gameId, field, value) {
  const { franchise, game } = findGame(gameId);
  if (!game) return;
  await save(async () => {
    const updated = await api.updateGame(gameId, { [field]: value });
    Object.assign(game, updated);
    // Title and notes are already shown as typed; only status / play_on change the row.
    if (field === "status" || field === "play_on") refreshGame(franchise, game);
    else refreshSummary(franchise);   // a title can appear in the "next up" pill
  });
}

async function editFranchise(franchiseId, field, value) {
  const franchise = findFranchise(franchiseId);
  if (!franchise) return;
  await save(async () => {
    const updated = await api.updateFranchise(franchiseId, { [field]: value });
    Object.assign(franchise, updated);
    if (field === "name") render();   // the A–Z position may change
  });
}

// Called by the detail panel. Errors are thrown back so the panel can show
// them and stay open.
async function saveGameFromPanel(gameId, changes) {
  saveState("Saving…");
  let updated;
  try {
    updated = await api.updateGame(gameId, changes);
  } catch (err) {
    saveState("");
    throw err;
  }
  const { franchise, game } = findGame(gameId);
  if (changes.franchise_id !== undefined && changes.franchise_id !== franchise.id) {
    // Moved: take it out of the old franchise, add it at the end of the new one.
    franchise.games = franchise.games.filter((g) => g.id !== gameId);
    const target = findFranchise(changes.franchise_id);
    target.games.push(updated);
    expanded.add(target.id);
    render();
  } else {
    Object.assign(game, updated);
    refreshGame(franchise, game);
  }
  saveState("Saved ✓", "saved");
}

// ---------- interaction ----------
// One listener for every editable field: it says what it edits with data-field.
document.addEventListener("change", (event) => {
  const el = event.target;
  const field = el.dataset.field;
  if (!field) return;
  let value = el.value;
  if (field === "play_on") value = value || null;      // "—" means none
  if ((field === "title" || field === "name") && !value.trim()) {
    showProblem("A name can't be empty.");
    load();
    return;
  }
  const row = el.closest("[data-game]");
  if (row) editGame(Number(row.dataset.game), field, value);
  else editFranchise(Number(el.closest("[data-franchise]").dataset.franchise), field, value);
});

// Enter in a one-line field saves it, like leaving the field.
document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.matches("input[data-field]")) event.target.blur();
});

// One click listener for the whole page; elements say what they do with data-action.
document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const action = target.dataset.action;

  if (action === "toggle") {
    // Clicks on the name field inside a franchise header don't toggle it.
    if (event.target.closest("input, textarea, select, button")) return;
    const id = Number(target.closest("[data-franchise]").dataset.franchise);
    expanded.has(id) ? expanded.delete(id) : expanded.add(id);
    target.closest(".fr").classList.toggle("open");   // no full re-render needed
  } else if (action === "dismiss") {
    $("problem").hidden = true;
  } else if (action === "open-panel") {
    const { franchise, game } = findGame(Number(target.closest("[data-game]").dataset.game));
    if (game) openGamePanel({ game, franchise, franchises, platforms, onSave: saveGameFromPanel });
  }
});

// ---------- start ----------
async function load() {
  try {
    [franchises, platforms] = await Promise.all([api.franchises(), api.platforms()]);
    render();
  } catch (err) {
    $("app").innerHTML = "";
    showProblem(err.message);
  }
}

load();
