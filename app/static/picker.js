// "What to play next": pick a random franchise and suggest its next game in
// play order. A franchise takes part only if its next game (the first one not
// finished or skipped) is released (not TBA) and not already being played.

const overlay = document.getElementById("picker");

let current = null;   // { franchises, onPlaying, onOpen }
let pick = null;      // { franchise, game }
let scope = "all";    // "all" or a franchise id

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const nextGame = (f) => f.games.find((g) => g.status !== "finished" && g.status !== "skip") || null;

// Every franchise whose next game can be suggested, with that game.
function candidates() {
  return current.franchises
    .map((franchise) => ({ franchise, game: nextGame(franchise) }))
    .filter(({ game }) => game && !game.release_tba && game.status !== "playing");
}

function roll() {
  const all = candidates();
  const pool = scope === "all" ? all : all.filter((c) => c.franchise.id === scope);
  if (!pool.length) { pick = null; return; }
  // Re-rolling avoids showing the same game twice in a row when there's a choice.
  const others = pool.length > 1 && pick ? pool.filter((c) => c.game.id !== pick.game.id) : pool;
  pick = others[Math.floor(Math.random() * others.length)];
}

function render() {
  const all = candidates();
  const options = [...all].sort((a, b) => a.franchise.name.localeCompare(b.franchise.name))
    .map(({ franchise }) => `<option value="${franchise.id}" ${scope === franchise.id ? "selected" : ""}>${esc(franchise.name)}</option>`)
    .join("");
  let card;
  if (pick) {
    const g = pick.game;
    const where = g.play_on ? `Play on <b>${esc(g.play_on)}</b>` : esc(g.platforms.join(" · ") || "platform: tbd");
    card = `<div class="roll-card">
        <div class="roll-fr">${esc(pick.franchise.name)}</div>
        <div class="roll-game"><a href="${esc(g.backloggd_link)}" target="_blank" rel="noopener" title="Open on Backloggd">${esc(g.title)}</a></div>
        <div class="roll-plat">${where}${g.released ? ` — ${esc(g.released)}` : ""}</div>
        ${g.notes ? `<div class="roll-note">“${esc(g.notes)}”</div>` : ""}
      </div>`;
  } else {
    card = `<div class="roll-card"><div class="roll-game">🎉 All caught up!</div>
        <div class="roll-plat">Nothing to suggest${scope === "all" ? "" : " in this franchise"}.</div></div>`;
  }
  overlay.innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-label="What to play next">
      <div class="filter-roll">Pick from:
        <select data-picker="scope" aria-label="Pick from"><option value="all">any franchise</option>${options}</select>
      </div>
      ${card}
      <div class="roll-hint">${all.length} franchise${all.length === 1 ? "" : "s"} in the draw. Unreleased (TBA) and already-playing games are left out.</div>
      <div class="roll-actions">
        <button type="button" class="btn-roll" data-picker="roll">🎲 Re-roll</button>
        ${pick ? `<button type="button" data-picker="playing">Set as Playing</button>
                  <button type="button" data-picker="open">Open details</button>` : ""}
        <button type="button" class="btn-ghost" data-picker="close">Close</button>
      </div>
    </div>`;
}

export function openPicker(options) {
  current = options;
  if (scope !== "all" && !current.franchises.some((f) => f.id === scope)) scope = "all";
  pick = null;
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
  const action = event.target.closest("[data-picker]")?.dataset.picker;
  if (action === "roll") { roll(); render(); }
  else if (action === "close") close();
  else if (action === "open") { close(); current.onOpen(pick.game, pick.franchise); }
  else if (action === "playing") {
    const chosen = pick;
    close();
    await current.onPlaying(chosen.game, chosen.franchise);
  }
});

overlay.addEventListener("change", (event) => {
  if (event.target.dataset.picker !== "scope") return;
  scope = event.target.value === "all" ? "all" : Number(event.target.value);
  pick = null;
  roll();
  render();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && overlay.classList.contains("on")) close();
});
