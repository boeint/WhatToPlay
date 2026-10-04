// WhatToPlay page: rendering and user interaction.
// All data comes from the backend through api.js.
import { api } from "./api.js";

// ---------- state ----------
let franchises = [];          // from GET /api/franchises, in custom order
const expanded = new Set();   // franchise ids; collapsed by default on every load

// Column widths are a per-device display preference, kept in this browser.
const COLUMN_DEFAULTS = { released: 92, platform: 200, status: 110, notes: 200, links: 80 };
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

function colgroup() {
  const cols = ["released", "platform", "status", "notes", "links"]
    .map((k) => `<col data-col="${k}" style="width:${columnWidths[k]}px">`).join("");
  return `<colgroup><col>${cols}<col style="width:34px"><col style="width:34px"></colgroup>`;
}

// ---------- rendering ----------
function renderGame(g) {
  const chips = g.platforms.length
    ? g.platforms.map((p) => `<span class="chip">${esc(p)}</span>`).join("")
    : `<span class="ph">+ platform</span>`;
  const options = STATUSES.map(([value, label]) =>
    `<option value="${value}" ${g.status === value ? "selected" : ""}>${label}</option>`).join("");
  const links = g.links.map((l) =>
    `<a href="${esc(l.url)}" target="_blank" rel="noopener" title="${esc(l.url)}">${esc(l.label)}</a>`).join("");
  return `<tr class="${g.status}" data-game="${g.id}">
    <td class="t-title"><div class="title-wrap"><span class="gmark">▹</span>
      <input value="${esc(g.title)}">
      <a class="bl" href="${esc(g.backloggd_link)}" target="_blank" rel="noopener" title="Open on Backloggd"><img src="https://backloggd.com/favicon.ico" alt="Backloggd"></a>
    </div></td>
    <td class="t-rel">${esc(g.released)}</td>
    <td><div class="plat-cell">${chips}</div></td>
    <td><select class="status ${g.status}">${options}</select></td>
    <td class="t-notes"><input value="${esc(g.notes)}"></td>
    <td class="t-links">${links}<button class="lnkbtn">＋</button></td>
    <td><div class="ord"><button title="Up">▲</button><button title="Down">▼</button></div></td>
    <td><button class="del" title="Delete game">×</button></td>
  </tr>`;
}

function renderFranchise(f) {
  const deck = onDeck(f);
  const total = f.games.length;
  const open = expanded.has(f.id);
  return `<div class="fr ${open ? "open" : ""}" data-franchise="${f.id}">
    <div class="fr-head" data-action="toggle">
      <span class="caret">▶</span>
      <input class="fr-title" value="${esc(f.name)}">
      <span class="fr-prog">${total - remaining(f)}/${total} done</span>
      ${deck
        ? `<span class="ondeck" title="Next up">▶ ${esc(deck.title)}</span>`
        : `<span class="fr-prog" style="color:var(--done)">✓ complete</span>`}
    </div>
    <div class="fr-body">
      <div class="fr-notes"><span class="lbl">Notes</span><textarea>${esc(f.notes)}</textarea></div>
      <div class="games-frame"><table>${colgroup()}<thead><tr>
        <th>Title</th>
        <th>Released<span class="rz" data-col="released"></span></th>
        <th>Platform<span class="rz" data-col="platform"></span></th>
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

function showError(message) {
  $("app").innerHTML = `<div class="error">⚠ ${esc(message)}</div>`;
}

// ---------- interaction ----------
// One click listener for the whole page; elements say what they do with data-action.
document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  // Clicks on inputs inside a franchise header (e.g. its name) don't toggle it.
  if (event.target.closest("input, textarea, select, button") && target.dataset.action === "toggle") return;
  const franchiseId = Number(target.closest("[data-franchise]")?.dataset.franchise);

  if (target.dataset.action === "toggle") {
    expanded.has(franchiseId) ? expanded.delete(franchiseId) : expanded.add(franchiseId);
    target.closest(".fr").classList.toggle("open");   // no full re-render needed
  }
});

// ---------- start ----------
async function load() {
  try {
    franchises = await api.franchises();
    render();
  } catch (err) {
    showError(err.message);
  }
}

load();
