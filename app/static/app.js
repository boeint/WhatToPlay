// WhatToPlay page: rendering and user interaction.
// All data comes from the backend through api.js.
import { api } from "./api.js";
import { confirmDialog, formDialog } from "./dialog.js";
import { BLANK_GAME, openGamePanel } from "./panel.js";
import { openPicker } from "./picker.js";
import { openStats } from "./stats.js";

// ---------- state ----------
let franchises = [];          // from GET /api/franchises, in custom order
let platforms = [];           // from GET /api/platforms, in display order
const expanded = new Set();   // franchise ids; collapsed by default on every load
let query = "";               // search box, normalized (see fold)
let statusFilter = "all";

// The chosen sort is a per-device preference, remembered in this browser.
let sortMode = "az";
try {
  sortMode = localStorage.getItem("whattoplay.sort") || "az";
} catch { /* storage unavailable (e.g. private mode): use the default */ }

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

// Lower case, accents removed: "Pokémon" -> "pokemon", so searches ignore both.
const fold = (text) => String(text ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

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
    <td class="t-plat"><div class="plat-cell" data-action="open-panel" title="Edit platforms">${chips}</div></td>
    <td class="t-playon"><span class="card-label">Play on</span><select data-field="play_on" aria-label="Play on" ${g.platforms.length ? "" : "disabled"}>${playOnOptions}</select></td>
    <td class="t-status"><select data-field="status" class="status ${g.status}" aria-label="Status">${statusOptions}</select></td>
    <td class="t-notes"><input data-field="notes" value="${esc(g.notes)}" aria-label="Notes" placeholder="Notes"></td>
    <td class="t-links">${links}<button class="lnkbtn" data-action="open-panel" title="Edit links">＋</button></td>
    <td class="t-ord"><div class="ord">
      <button data-action="move-up" title="Move up" ${index === 0 ? "disabled" : ""}>▲</button>
      <button data-action="move-down" title="Move down" ${index === games.length - 1 ? "disabled" : ""}>▼</button>
    </div></td>
    <td class="t-del"><button class="del" data-action="delete-game" title="Delete game">×</button></td>
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

// ---------- search / filter / sort ----------
const isFiltering = () => query !== "" || statusFilter !== "all";

// The games of a franchise that match the search and status filter,
// or null when the whole franchise should be hidden.
function visibleGames(f) {
  if (!isFiltering()) return f.games;
  const nameMatches = query !== "" && fold(f.name).includes(query);
  const games = f.games.filter((g) => {
    const text = [g.title, g.notes, g.play_on, ...g.platforms].map(fold).join("\n");
    const matchesQuery = !query || nameMatches || text.includes(query);
    const matchesStatus = statusFilter === "all" || g.status === statusFilter;
    return matchesQuery && matchesStatus;
  });
  if (games.length) return games;
  // No matching game: still show a franchise whose *name* matches, unless a status filter is on.
  return nameMatches && statusFilter === "all" ? [] : null;
}

function sortedFranchises() {
  const byName = (a, b) => a.name.localeCompare(b.name);
  if (sortMode === "custom") return franchises;              // the server's order
  if (sortMode === "remaining") return [...franchises].sort((a, b) => remaining(b) - remaining(a) || byName(a, b));
  return [...franchises].sort(byName);                       // A–Z, "The" counts
}

function renderFranchise(f, games = f.games) {
  // While searching or filtering, franchises with matches open automatically.
  const open = expanded.has(f.id) || (isFiltering() && games.length > 0);
  return `<div class="fr ${open ? "open" : ""}" data-franchise="${f.id}">
    <div class="fr-head" data-action="toggle">
      <span class="drag-handle fr-drag" draggable="true" title="Drag to reorder franchises">⠿</span>
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
      </tr></thead><tbody>${games.map((g) => renderGame(g, f.games.indexOf(g), f.games)).join("")}</tbody></table>
      <div class="fr-foot"><button data-action="add-game">+ Add game to ${esc(f.name)}</button>
        <span class="reorder-hint">Clear the search and status filter to reorder.</span></div></div>
    </div>
  </div>`;
}

// Redraw one whole franchise block (after adding / deleting games).
function refreshFranchise(franchise) {
  if (isFiltering()) return render();   // what's visible may have changed
  const block = document.querySelector(`.fr[data-franchise="${franchise.id}"]`);
  if (block) block.outerHTML = renderFranchise(franchise);
  renderStats();
}

function render() {
  const app = $("app");
  const html = sortedFranchises().map((f) => {
    const games = visibleGames(f);
    return games === null ? "" : renderFranchise(f, games);
  }).join("");
  app.classList.toggle("filtering", isFiltering());
  app.classList.toggle("custom-sort", sortMode === "custom" && !isFiltering());
  app.innerHTML = html || (franchises.length
    ? `<div class="empty">No matches. <button class="btn-ghost" data-action="reset-filters">Reset</button></div>`
    : `<div class="empty"><p>Your backlog is empty.</p>
        <button class="btn-primary" data-action="import">Import a backup</button>
        <button data-action="add-franchise">Start with a new franchise</button></div>`);
  renderStats();
}

function renderStats() {
  const games = franchises.flatMap((f) => f.games);
  const count = (status) => games.filter((g) => g.status === status).length;
  const s = (n) => (n === 1 ? "" : "s");
  $("stats").innerHTML =
    `<span>📚 <b>${franchises.length}</b> franchise${s(franchises.length)}</span>` +
    `<span>🎮 <b>${games.length}</b> game${s(games.length)}</span>` +
    `<span>✅ <b>${count("finished")}</b> done</span><span>▶ <b>${count("playing")}</b> playing</span>` +
    `<span>⏳ <b>${games.filter(isOpenGame).length}</b> left</span>`;
}

// Redraw just one game row and its franchise's summary (keeps focus elsewhere intact).
function refreshGame(franchise, game) {
  if (isFiltering()) return render();   // the game may no longer match the filter
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

let toastTimer;
function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("on"), 2500);
}

// Open a game's franchise, scroll its row into view and flash it briefly.
function reveal(franchise, game) {
  expanded.add(franchise.id);
  render();
  const row = document.querySelector(`tr[data-game="${game.id}"]`);
  row?.scrollIntoView({ block: "center", behavior: "smooth" });
  row?.classList.add("flash");
  setTimeout(() => row?.classList.remove("flash"), 1600);
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

async function reorderFranchises(franchiseIds) {
  const byId = new Map(franchises.map((f) => [f.id, f]));
  franchises = franchiseIds.map((id) => byId.get(id));
  render();
  await save(() => api.setFranchiseOrder(franchiseIds));
}

// Move `id` to just before / after `targetId` in a list of ids.
function moveId(ids, id, targetId, after) {
  const rest = ids.filter((x) => x !== id);
  rest.splice(rest.indexOf(targetId) + (after ? 1 : 0), 0, id);
  return rest;
}

// Drag and drop, only from a ⠿ handle:
//  - a game, within its own franchise;
//  - a franchise (handle shown only in custom sort), among the franchises.
let dragging = null;   // { kind: "game" | "franchise", id, franchiseId }

function clearDropMarks() {
  document.querySelectorAll(".drop-before, .drop-after, .dragging")
    .forEach((el) => el.classList.remove("drop-before", "drop-after", "dragging"));
}

// The element a drop would land on (a game row, or a franchise block), if allowed.
function dropTarget(event) {
  if (!dragging) return null;
  if (dragging.kind === "franchise") return event.target.closest(".fr[data-franchise]");
  const row = event.target.closest("tr[data-game]");
  const sameFranchise = row && Number(row.closest("[data-franchise]").dataset.franchise) === dragging.franchiseId;
  return sameFranchise ? row : null;
}

document.addEventListener("dragstart", (event) => {
  const handle = event.target.closest?.(".drag-handle");
  if (!handle) return;
  const row = handle.closest("tr[data-game]");
  const block = handle.closest(".fr[data-franchise]");
  const moving = row || block;                          // a game handle sits inside a row
  dragging = row
    ? { kind: "game", id: Number(row.dataset.game), franchiseId: Number(block.dataset.franchise) }
    : { kind: "franchise", id: Number(block.dataset.franchise) };
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", String(dragging.id));   // required by Firefox
  event.dataTransfer.setDragImage(moving, 20, 20);                  // drag the whole row / block
  moving.classList.add("dragging");
});

document.addEventListener("dragover", (event) => {
  const target = dropTarget(event);
  if (!target) return;
  event.preventDefault();   // "a drop is allowed here"
  // For franchises, compare with the header's middle (blocks can be tall when open).
  const box = (target.querySelector(".fr-head") || target).getBoundingClientRect();
  const after = event.clientY > box.top + box.height / 2;
  document.querySelectorAll(".drop-before, .drop-after")
    .forEach((el) => el.classList.remove("drop-before", "drop-after"));
  target.classList.add(after ? "drop-after" : "drop-before");
});

document.addEventListener("drop", (event) => {
  const target = dropTarget(event);
  if (!target) return;
  event.preventDefault();
  const after = target.classList.contains("drop-after");
  if (dragging.kind === "game") {
    const franchise = findFranchise(dragging.franchiseId);
    const targetId = Number(target.dataset.game);
    if (targetId !== dragging.id) reorderGames(franchise, moveId(franchise.games.map((g) => g.id), dragging.id, targetId, after));
  } else {
    const targetId = Number(target.dataset.franchise);
    if (targetId !== dragging.id) reorderFranchises(moveId(franchises.map((f) => f.id), dragging.id, targetId, after));
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
  if (el.dataset.platform) {             // renaming a platform in Settings
    const name = el.value.trim();
    if (name) platformChange(() => api.renamePlatform(Number(el.dataset.platform), name));
    return;
  }
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
  if (event.key !== "Enter") return;
  if (event.target.matches("input[data-field], input[data-platform]")) {
    event.preventDefault();               // inside Settings, Enter must not submit the whole dialog
    event.target.blur();
  } else if (event.target.matches("input[name=new_platform]")) {
    event.preventDefault();
    addPlatform();
  }
});

// One click listener for the whole page; elements say what they do with data-action.
document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const action = target.dataset.action;

  if (action === "toggle") {
    // Clicks on the name field or the drag handle inside a franchise header don't toggle it.
    if (event.target.closest("input, textarea, select, button, .drag-handle")) return;
    const id = Number(target.closest("[data-franchise]").dataset.franchise);
    expanded.has(id) ? expanded.delete(id) : expanded.add(id);
    target.closest(".fr").classList.toggle("open");   // no full re-render needed
  } else if (action === "dismiss") {
    $("problem").hidden = true;
  } else if (action === "add-franchise") {
    addFranchise();
  } else if (action === "pick") {
    openPicker({
      franchises,
      onOpen: (game, franchise) => openGame(game, franchise),
      onPlaying: (game, franchise) => save(async () => {
        Object.assign(game, await api.updateGame(game.id, { status: "playing" }));
        reveal(franchise, game);
        toast(`Now playing: ${game.title}`);
      }),
    });
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
  } else if (action === "stats") {
    openStats({ franchises, onOpen: (game, franchise) => openGame(game, franchise) });
  } else if (action === "settings") {
    openSettings();
  } else if (action === "reset-ai-instructions") {
    $("ai-instructions").value = defaultAiInstructions;
  } else if (action === "platform-add") {
    addPlatform();
  } else if (action.startsWith("platform-")) {
    const id = Number(target.closest("[data-platform-id]").dataset.platformId);
    if (action === "platform-up") movePlatform(id, -1);
    else if (action === "platform-down") movePlatform(id, +1);
    else if (action === "platform-delete") platformChange(() => api.deletePlatform(id));
  } else if (action === "restore-backup") {
    restoreBackup();
  } else if (action === "export") {
    exportData();
  } else if (action === "import") {
    $("import-file").click();
  } else if (action === "expand-all") {
    franchises.forEach((f) => expanded.add(f.id));
    render();
  } else if (action === "collapse-all") {
    expanded.clear();
    render();
  } else if (action === "reset-filters") {
    $("search").value = "";
    $("filter").value = "all";
    query = "";
    statusFilter = "all";
    render();
  }
});

// ---------- export / import ----------
function saveFile(blob, filename) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 10_000);
}

async function exportData() {
  try {
    const { blob, filename } = await api.exportAll();
    saveFile(blob, filename);
    toast(`Exported ${filename}`);
  } catch (err) {
    showProblem(`Export failed: ${err.message}`);
  }
}

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

async function importData(file) {
  // 1. Read and sanity-check the file in the browser before anything else.
  let data;
  try {
    data = JSON.parse(await file.text());
  } catch {
    return showProblem(`"${file.name}" isn't a valid JSON file.`);
  }
  if (data?.format !== "whattoplay-export") {
    return showProblem(`"${file.name}" isn't a WhatToPlay export file (exports made by the old app can't be imported).`);
  }
  // 2. Say exactly what will happen.
  const fileGames = (data.franchises || []).reduce((n, f) => n + (f.games || []).length, 0);
  const nowGames = franchises.reduce((n, f) => n + f.games.length, 0);
  const when = data.exported_at ? ` (exported ${new Date(data.exported_at).toLocaleDateString()})` : "";
  const ok = await confirmDialog(
    `This file has ${plural((data.franchises || []).length, "franchise")} and ${plural(fileGames, "game")}${when}. ` +
    `Importing replaces all your current data: ${plural(franchises.length, "franchise")} and ${plural(nowGames, "game")}. ` +
    "A backup of your current data is downloaded first.",
    "Back up & import", { danger: true });
  if (!ok) return;
  // 3. Backup first; no backup, no import.
  try {
    const { blob, filename } = await api.exportAll();
    saveFile(blob, filename.replace(".json", "-before-import.json"));
  } catch (err) {
    return showProblem(`Import cancelled: the backup could not be made (${err.message}).`);
  }
  // 4. Import (all or nothing on the server), then show the new data.
  saveState("Importing…");
  try {
    const counts = await api.importAll(data);
    saveState("Saved ✓", "saved");
    expanded.clear();
    await load();
    toast(`Imported ${plural(counts.franchises, "franchise")} and ${plural(counts.games, "game")}`);
  } catch (err) {
    saveState("");
    showProblem(`Not imported, nothing was changed: ${err.message}`);
  }
}

// ---------- settings ----------
let defaultAiInstructions = "";
let platformsChanged = false;   // reload the backlog when the dialog closes (renamed chips)

function renderPlatformList() {
  return platforms.map((p, i) => `<div class="platform-row" data-platform-id="${p.id}">
      <div class="ord">
        <button type="button" data-action="platform-up" title="Move up" ${i === 0 ? "disabled" : ""}>▲</button>
        <button type="button" data-action="platform-down" title="Move down" ${i === platforms.length - 1 ? "disabled" : ""}>▼</button>
      </div>
      <input data-platform="${p.id}" value="${esc(p.name)}" maxlength="50" aria-label="Platform name">
      <span class="used" title="Games listing this platform">${p.used_by ? plural(p.used_by, "game") : "unused"}</span>
      <button type="button" class="del" data-action="platform-delete" ${p.used_by ? "disabled" : ""}
        title="${p.used_by ? `Used by ${plural(p.used_by, "game")}: remove it from them first` : "Delete"}">×</button>
    </div>`).join("");
}

// Run one platform change, then refresh the list shown in the dialog.
async function platformChange(work) {
  const box = document.querySelector(".platform-list");
  const error = document.querySelector("#dialog [data-out=error]");
  try {
    await withIndicator(work);
    error.textContent = "";
  } catch (err) {
    error.textContent = err.message;
  }
  platforms = await api.platforms();
  platformsChanged = true;
  if (box) box.innerHTML = renderPlatformList();
}

function movePlatform(id, step) {
  const ids = platforms.map((p) => p.id);
  const from = ids.indexOf(id);
  const to = from + step;
  if (to < 0 || to >= ids.length) return;
  [ids[from], ids[to]] = [ids[to], ids[from]];
  platformChange(() => api.setPlatformOrder(ids));
}

function addPlatform() {
  const input = document.querySelector("#dialog [name=new_platform]");
  const name = input.value.trim();
  if (!name) return;
  platformChange(async () => {
    await api.createPlatform(name);
    input.value = "";
  });
}

async function openSettings() {
  let s;
  try {
    s = await api.settings();
  } catch (err) {
    return showProblem(`Could not load the settings: ${err.message}`);
  }
  defaultAiInstructions = s.default_ai_instructions;
  await formDialog({
    title: "Settings",
    okLabel: "Save",
    body: `<div class="settings-form">
      <div class="field">
        <label class="check"><input type="checkbox" name="ai_enabled" ${s.ai_enabled ? "checked" : ""}>
          AI assistant</label>
        <div class="hint">Lets Claude Code read your backlog and add games for you, through
          <code>${esc(location.origin)}/mcp</code>. When off, that address refuses every request.</div>
      </div>
      <div class="field">
        <div class="row"><label for="ai-instructions">AI instructions</label>
          <button type="button" class="lnkbtn" data-action="reset-ai-instructions">Reset to default</button></div>
        <textarea id="ai-instructions" name="ai_instructions">${esc(s.ai_instructions)}</textarea>
        <div class="hint">Claude reads these before adding or changing anything.</div>
      </div>
      <div class="field">
        <label>Platforms</label>
        <div class="hint" style="margin:0 0 8px">Changes to platforms are saved immediately. A platform can be
          deleted only when no game uses it.</div>
        <div class="platform-list">${renderPlatformList()}</div>
        <div class="platform-add">
          <input name="new_platform" maxlength="50" placeholder="New platform, e.g. NSO" aria-label="New platform">
          <button type="button" data-action="platform-add">Add</button>
        </div>
      </div>
    </div>`,
    onSubmit: async (form) => {
      await withIndicator(() => api.updateSettings({
        ai_enabled: form.elements.ai_enabled.checked,
        ai_instructions: form.elements.ai_instructions.value,
      }));
      toast("Settings saved");
    },
  });
  if (platformsChanged) {
    platformsChanged = false;
    await load();   // renamed platforms appear in the games' chips
  }
}

// ---------- backups on the server: status line + restore ----------
// "today 03:30", "yesterday 03:30", or "Oct 2, 03:30" (in this device's time zone).
function when(iso) {
  const d = new Date(iso);
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const days = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 86_400_000);
  if (days === 0) return `today ${time}`;
  if (days === 1) return `yesterday ${time}`;
  return `${d.toLocaleDateString([], { month: "short", day: "numeric" })}, ${time}`;
}

async function loadBackupStatus() {
  const el = $("backup-status");
  let s;
  try {
    s = await api.backups();
  } catch {
    el.textContent = "";
    return;
  }
  const failedLast = s.last_error && (!s.latest || s.last_error.at > s.latest.written_at);
  let line;
  if (!s.enabled) {
    line = `<span class="warn">⚠ Daily backups are off: ${esc(s.reason)}.</span>`;
  } else if (failedLast) {
    line = `<span class="bad">✖ The last backup failed (${esc(when(s.last_error.at))}): ${esc(s.last_error.message)}</span>`;
  } else if (s.latest) {
    line = `✓ Last backup ${esc(when(s.latest.written_at))} · ${plural(s.daily_count, "daily backup")} kept · next ${esc(when(s.next_at))}`;
  } else {
    line = `Daily backups on · first one ${esc(when(s.next_at))}`;
  }
  const restore = s.enabled && s.files.length ? ` · <button data-action="restore-backup">Restore a backup…</button>` : "";
  el.innerHTML = line + restore;
}

async function restoreBackup() {
  let s;
  try {
    s = await api.backups();
  } catch (err) {
    return showProblem(`Could not list the backups: ${err.message}`);
  }
  const options = s.files.map((f, i) => `<label>
      <input type="radio" name="backup" value="${esc(f.name)}" ${i === 0 ? "checked" : ""}>
      <span>${esc(when(f.written_at))}</span>
      ${f.kind === "before-restore" ? `<span class="tag" title="Saved automatically just before a restore">before a restore</span>` : ""}
      <span class="meta">${Math.round(f.size / 1024)} KB</span></label>`).join("");
  await formDialog({
    title: "Restore a backup",
    okLabel: "Restore",
    danger: true,
    body: `<p class="dialog-text">Restoring replaces all your current data with the chosen backup.
      A copy of the current data is saved first, so this can be undone from this same list.</p>
      <div class="backup-list">${options}</div>`,
    onSubmit: async (form) => {
      const name = form.elements.backup.value;
      const result = await withIndicator(() => api.restoreBackup(name));
      expanded.clear();
      await load();
      toast(`Restored: ${plural(result.franchises, "franchise")} and ${plural(result.games, "game")}`);
    },
  });
}

$("import-file").addEventListener("change", (event) => {
  const file = event.target.files[0];
  event.target.value = "";   // so choosing the same file again still triggers
  if (file) importData(file);
});

// ---------- search, filter, sort ----------
let searchTimer;
$("search").addEventListener("input", () => {
  clearTimeout(searchTimer);   // wait for a pause in typing before redrawing 560 games
  searchTimer = setTimeout(() => { query = fold($("search").value); render(); }, 150);
});
$("filter").addEventListener("change", () => { statusFilter = $("filter").value; render(); });
$("sort").value = sortMode;
$("sort").addEventListener("change", () => {
  sortMode = $("sort").value;
  try { localStorage.setItem("whattoplay.sort", sortMode); } catch { /* private mode */ }
  render();
});

// ---------- column resizing ----------
// Drag a column header's right edge; the width applies to every franchise table
// and is remembered in this browser.
let resizing = null;   // { col, startX, startWidth }

document.addEventListener("mousedown", (event) => {
  const edge = event.target.closest(".rz");
  if (!edge) return;
  event.preventDefault();
  resizing = { col: edge.dataset.col, startX: event.clientX, startWidth: columnWidths[edge.dataset.col] };
  document.body.classList.add("resizing");
});

document.addEventListener("mousemove", (event) => {
  if (!resizing) return;
  const width = Math.max(50, resizing.startWidth + event.clientX - resizing.startX);
  columnWidths[resizing.col] = width;
  document.querySelectorAll(`col[data-col="${resizing.col}"]`).forEach((c) => { c.style.width = `${width}px`; });
});

document.addEventListener("mouseup", () => {
  if (!resizing) return;
  resizing = null;
  document.body.classList.remove("resizing");
  try { localStorage.setItem("whattoplay.cols", JSON.stringify(columnWidths)); } catch { /* private mode */ }
});

// ---------- fresh data across devices ----------
// Coming back to this tab after a while (e.g. after editing on the phone):
// quietly reload, unless something is being edited here right now.
const REFRESH_AFTER_MS = 30_000;
let lastLoaded = 0;

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || Date.now() - lastLoaded < REFRESH_AFTER_MS) return;
  const busy = !$("panel").hidden
    || document.querySelector(".ov.on")
    || document.activeElement?.matches("input, textarea, select");
  if (!busy) load();
});

// ---------- start ----------
async function load() {
  try {
    [franchises, platforms] = await Promise.all([api.franchises(), api.platforms()]);
    lastLoaded = Date.now();
    render();
    loadBackupStatus();   // not awaited: the list doesn't wait for it
  } catch (err) {
    $("app").innerHTML = "";
    showProblem(err.message);
  }
}

load();
