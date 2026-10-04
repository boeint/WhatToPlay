// WhatToPlay page: rendering and user interaction.
// All data comes from the backend through api.js.
import { api } from "./api.js";
import { confirmDialog, formDialog } from "./dialog.js";
import { BLANK_GAME, openGamePanel } from "./panel.js";

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
function renderGame(g, index, games) {
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
    <td class="t-title"><div class="title-wrap"><span class="drag-handle" draggable="true" title="Drag to reorder">⠿</span>
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
    <td><div class="ord">
      <button data-action="move-up" title="Move up" ${index === 0 ? "disabled" : ""}>▲</button>
      <button data-action="move-down" title="Move down" ${index === games.length - 1 ? "disabled" : ""}>▼</button>
    </div></td>
    <td><button class="del" data-action="delete-game" title="Delete game">×</button></td>
  </tr>`;
}

// The part of a franchise header that depends on its games' statuses.
function renderSummary(f) {
  const deck = onDeck(f);
  const total = f.games.length;
  if (!total) return `<span class="fr-prog">no games yet</span>`;
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
      <div class="fr-actions">
        <button data-action="add-game">+ Game</button>
        <button class="del" data-action="delete-franchise" title="Delete franchise">🗑</button>
      </div>
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
      </tr></thead><tbody>${f.games.map(renderGame).join("")}</tbody></table>
      <div class="fr-foot"><button data-action="add-game">+ Add game to ${esc(f.name)}</button></div></div>
    </div>
  </div>`;
}

// Redraw one whole franchise block (after adding / deleting games).
function refreshFranchise(franchise) {
  const block = document.querySelector(`.fr[data-franchise="${franchise.id}"]`);
  if (block) block.outerHTML = renderFranchise(franchise);
  renderStats();
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
  if (row) row.outerHTML = renderGame(game, franchise.games.indexOf(game), franchise.games);
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

// Run a request with the "Saving…" indicator; errors are thrown back to the
// caller (the panel or a dialog shows them and stays open).
async function withIndicator(request) {
  saveState("Saving…");
  try {
    const result = await request();
    saveState("Saved ✓", "saved");
    return result;
  } catch (err) {
    saveState("");
    throw err;
  }
}

function openGame(game, franchise) {
  openGamePanel({
    mode: "edit", game, franchise, franchises, platforms,
    onSave: saveGameFromPanel, onDelete: deleteGame,
  });
}

function openNewGame(franchise) {
  openGamePanel({
    mode: "create", game: { ...BLANK_GAME }, franchise, franchises, platforms,
    onSave: (_id, data) => createGame(franchise, data),
  });
}

// From the panel in create mode: `data` holds the filled-in fields.
async function createGame(franchise, data) {
  const target = findFranchise(data.franchise_id ?? franchise.id);
  delete data.franchise_id;                       // it's in the URL instead
  const created = await withIndicator(() => api.createGame(target.id, data));
  target.games.push(created);
  expanded.add(target.id);
  refreshFranchise(target);
}

async function deleteGame(gameId) {
  const { franchise } = findGame(gameId);
  await withIndicator(() => api.deleteGame(gameId));
  franchise.games = franchise.games.filter((g) => g.id !== gameId);
  refreshFranchise(franchise);
}

async function deleteFranchise(franchise) {
  const count = franchise.games.length;
  const what = count ? `"${franchise.name}" and its ${count} game${count === 1 ? "" : "s"}` : `"${franchise.name}"`;
  if (!(await confirmDialog(`Delete ${what}?`, "Delete", { danger: true }))) return;
  await save(async () => {
    await api.deleteFranchise(franchise.id);
    franchises = franchises.filter((f) => f.id !== franchise.id);
    render();
  });
}

async function addFranchise() {
  await formDialog({
    title: "New franchise",
    okLabel: "Create",
    body: `<div class="field"><label for="new-franchise">Name</label>
        <input type="text" id="new-franchise" name="name" maxlength="200" autocomplete="off"></div>
      <div class="field"><label class="check"><input type="checkbox" name="with_game" checked>
        Also add a game with this name (for standalone games)</label></div>`,
    onSubmit: async (form) => {
      const name = form.elements.name.value.trim();
      if (!name) throw new Error("Please enter a name.");
      const games = form.elements.with_game.checked ? [{ title: name }] : [];
      const created = await withIndicator(() => api.createFranchise({ name, games }));
      franchises.push(created);
      expanded.add(created.id);
      render();
      document.querySelector(`.fr[data-franchise="${created.id}"]`)?.scrollIntoView({ block: "center" });
    },
  });
}

// ---------- reordering ----------
// Show the new order immediately, then save the complete order. If the server
// refuses (e.g. a game was deleted on another device), save() reloads the real data.
async function reorderGames(franchise, gameIds) {
  const byId = new Map(franchise.games.map((g) => [g.id, g]));
  franchise.games = gameIds.map((id) => byId.get(id));
  refreshFranchise(franchise);
  await save(() => api.setGameOrder(franchise.id, gameIds));
}

function moveGame(franchise, gameId, step) {
  const ids = franchise.games.map((g) => g.id);
  const from = ids.indexOf(gameId);
  const to = from + step;
  if (to < 0 || to >= ids.length) return;
  [ids[from], ids[to]] = [ids[to], ids[from]];
  reorderGames(franchise, ids);
}

// Drag and drop, only from the ⠿ handle, only within the same franchise.
let dragging = null;   // { franchiseId, gameId }

function clearDropMarks() {
  document.querySelectorAll(".drop-before, .drop-after, .dragging")
    .forEach((el) => el.classList.remove("drop-before", "drop-after", "dragging"));
}

document.addEventListener("dragstart", (event) => {
  const handle = event.target.closest?.(".drag-handle");
  if (!handle) return;
  const row = handle.closest("tr[data-game]");
  dragging = {
    franchiseId: Number(row.closest("[data-franchise]").dataset.franchise),
    gameId: Number(row.dataset.game),
  };
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", row.dataset.game);   // required by Firefox
  event.dataTransfer.setDragImage(row, 20, 20);                  // drag the whole row
  row.classList.add("dragging");
});

document.addEventListener("dragover", (event) => {
  if (!dragging) return;
  const row = event.target.closest("tr[data-game]");
  if (!row || Number(row.closest("[data-franchise]").dataset.franchise) !== dragging.franchiseId) return;
  event.preventDefault();   // "a drop is allowed here"
  const box = row.getBoundingClientRect();
  const after = event.clientY > box.top + box.height / 2;
  document.querySelectorAll(".drop-before, .drop-after")
    .forEach((el) => el.classList.remove("drop-before", "drop-after"));
  row.classList.add(after ? "drop-after" : "drop-before");
});

document.addEventListener("drop", (event) => {
  if (!dragging) return;
  const row = event.target.closest("tr[data-game]");
  if (!row) return;
  event.preventDefault();
  const franchise = findFranchise(dragging.franchiseId);
  const targetId = Number(row.dataset.game);
  const after = row.classList.contains("drop-after");
  const ids = franchise.games.map((g) => g.id).filter((id) => id !== dragging.gameId);
  if (targetId !== dragging.gameId) {
    ids.splice(ids.indexOf(targetId) + (after ? 1 : 0), 0, dragging.gameId);
    reorderGames(franchise, ids);
  }
  clearDropMarks();
  dragging = null;
});

document.addEventListener("dragend", () => {
  clearDropMarks();
  dragging = null;
});

// From the panel in edit mode. Errors are thrown back so the panel can show
// them and stay open.
async function saveGameFromPanel(gameId, changes) {
  const updated = await withIndicator(() => api.updateGame(gameId, changes));
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
  } else if (action === "add-franchise") {
    addFranchise();
  } else if (action === "open-panel" || action === "delete-game" || action.startsWith("move-")) {
    const { franchise, game } = findGame(Number(target.closest("[data-game]").dataset.game));
    if (!game) return;
    if (action === "open-panel") openGame(game, franchise);
    else if (action === "move-up") moveGame(franchise, game.id, -1);
    else if (action === "move-down") moveGame(franchise, game.id, +1);
    else confirmDialog(`Delete "${game.title}"?`, "Delete", { danger: true }).then((yes) => {
      if (yes) save(() => deleteGame(game.id));
    });
  } else if (action === "add-game" || action === "delete-franchise") {
    const franchise = findFranchise(Number(target.closest("[data-franchise]").dataset.franchise));
    if (action === "add-game") openNewGame(franchise);
    else deleteFranchise(franchise);
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
