// "Your stats": totals, finished games per year, what's left in the backlog
// (by length and by franchise), and every finished game, newest first.
// Hours come from each game's length (HowLongToBeat "Main Story"), so they're estimates.

const overlay = document.getElementById("stats-view");
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const LENGTHS = [["Short", "under 10 h", 1, 10], ["Medium", "10–30 h", 10, 30], ["Long", "30 h+", 30, Infinity]];

let current = null;   // { franchises, onOpen }

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const hoursOf = (games) => games.reduce((sum, g) => sum + (g.length_hours || 0), 0);
const known = (games) => games.filter((g) => g.length_hours).length;
// " · ~120 h", or nothing when none of the games has a length.
const hoursSuffix = (games) => (known(games) ? ` · ~${hoursOf(games).toLocaleString()} h` : "");

// "~120 h", plus how many games it leaves out for lack of a length.
function hoursLabel(games) {
  if (!games.length) return "";
  const missing = games.length - known(games);
  if (missing === games.length) return "no lengths yet";
  return `~${hoursOf(games).toLocaleString()} h${missing ? ` <span class="st-muted">(${missing} without a length)</span>` : ""}`;
}

function tile(label, value, detail) {
  return `<div class="st-tile"><div class="st-label">${label}</div><div class="st-value">${value}</div>
    <div class="st-detail">${detail}</div></div>`;
}

function render() {
  const all = current.franchises.flatMap((f) => f.games.map((game) => ({ game, franchise: f })));
  const games = all.map((x) => x.game);
  const by = (status) => games.filter((g) => g.status === status);
  const finished = all.filter((x) => x.game.status === "finished");
  const playing = by("playing");
  const left = games.filter((g) => g.status === "unplayed" || g.status === "playing");
  const counted = games.length - by("skip").length;            // skipped games don't count against you
  const percent = counted ? Math.round((finished.length / counted) * 100) : 0;

  // Finished per year (by finished date), newest first; games without a date last.
  const years = new Map();
  for (const x of finished) {
    const year = x.game.finished_on ? x.game.finished_on.slice(0, 4) : "Date unknown";
    if (!years.has(year)) years.set(year, []);
    years.get(year).push(x);
  }
  const yearKeys = [...years.keys()].sort((a, b) => (a === "Date unknown") - (b === "Date unknown") || b.localeCompare(a));
  const most = Math.max(1, ...[...years.values()].map((list) => list.length));
  const yearBars = yearKeys.map((year) => {
    const list = years.get(year);
    return `<div class="st-bar-row"><span class="st-bar-label">${esc(year)}</span>
      <span class="st-bar"><span style="width:${(list.length / most) * 100}%"></span></span>
      <span class="st-bar-value">${plural(list.length, "game")}${hoursSuffix(list.map((x) => x.game))}</span></div>`;
  }).join("");

  // The backlog by length (the picker's buckets).
  const bucketMost = Math.max(1, ...LENGTHS.map(([, , min, max]) => left.filter((g) => g.length_hours >= min && g.length_hours < max).length));
  const buckets = LENGTHS.map(([name, range, min, max]) => {
    const list = left.filter((g) => g.length_hours >= min && g.length_hours < max);
    return `<div class="st-bar-row"><span class="st-bar-label">${name} <span class="st-muted">${range}</span></span>
      <span class="st-bar"><span style="width:${(list.length / bucketMost) * 100}%"></span></span>
      <span class="st-bar-value">${plural(list.length, "game")}${hoursSuffix(list)}</span></div>`;
  }).join("");
  const noLength = left.length - known(left);

  // Franchises with the most hours left.
  const biggest = current.franchises
    .map((f) => ({ f, open: f.games.filter((g) => g.status === "unplayed" || g.status === "playing") }))
    .filter(({ open }) => open.length)
    .sort((a, b) => hoursOf(b.open) - hoursOf(a.open) || b.open.length - a.open.length)
    .slice(0, 5)
    .map(({ f, open }) => `<li><span>${esc(f.name)}</span><span class="st-muted">${plural(open.length, "game")}${hoursSuffix(open)}</span></li>`)
    .join("");

  // Every finished game, grouped by year, newest first.
  const finishedList = yearKeys.map((year) => {
    const rows = years.get(year)
      .sort((a, b) => (b.game.finished_on || "").localeCompare(a.game.finished_on || ""))
      .map(({ game: g, franchise: f }) => {
        const date = g.finished_on ? `${Number(g.finished_on.slice(8, 10))} ${MONTHS[Number(g.finished_on.slice(5, 7)) - 1]}` : "";
        return `<li>${date ? `<span class="st-date">${date}</span>` : ""}
          <button type="button" class="st-game" data-stats="open" data-game="${g.id}">${esc(g.title)}</button>
          <span class="st-muted">${esc(f.name)}${g.length_hours ? ` · ~${g.length_hours} h` : ""}</span></li>`;
      }).join("");
    return `<h4>${esc(year)}</h4><ul class="st-finished">${rows}</ul>`;
  }).join("");

  overlay.innerHTML = `<div class="modal stats-modal" role="dialog" aria-modal="true" aria-label="Your stats">
      <div class="st-head"><h2>Your stats</h2>
        <button type="button" class="btn-ghost" data-stats="close" aria-label="Close">Close</button></div>
      <div class="st-tiles">
        ${tile("Finished", finished.length, `${percent}% of your games${by("skip").length ? ", skips aside" : ""}<br>${hoursLabel(finished.map((x) => x.game))}`)}
        ${tile("Playing", playing.length, hoursLabel(playing) || "nothing right now")}
        ${tile("Left to play", left.length, hoursLabel(left))}
        ${tile("Skipped", by("skip").length, "not counted")}
      </div>
      <h3>Finished per year</h3>
      ${yearBars || `<p class="st-muted">Nothing finished yet.</p>`}
      <h3>What's left, by length</h3>
      ${buckets}
      ${noLength ? `<p class="st-muted st-note">${plural(noLength, "game")} left without a length (not out yet, or no time on HowLongToBeat).</p>` : ""}
      <h3>Biggest backlogs</h3>
      <ul class="st-biggest">${biggest || `<li class="st-muted">Nothing left to play.</li>`}</ul>
      <h3>Finished games</h3>
      ${finishedList || `<p class="st-muted">Nothing finished yet.</p>`}
      <p class="st-muted st-note">Hours are estimates from each game's length (HowLongToBeat "Main Story").</p>
    </div>`;
}

export function openStats(options) {
  current = options;
  render();
  overlay.classList.add("on");
  overlay.querySelector('[data-stats="close"]').focus();
}

function close() {
  overlay.classList.remove("on");
}

overlay.addEventListener("click", (event) => {
  if (event.target === overlay) return close();   // click outside the box
  const button = event.target.closest("[data-stats]");
  if (!button) return;
  if (button.dataset.stats === "close") close();
  else if (button.dataset.stats === "open") {
    const id = Number(button.dataset.game);
    const franchise = current.franchises.find((f) => f.games.some((g) => g.id === id));
    close();
    current.onOpen(franchise.games.find((g) => g.id === id), franchise);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && overlay.classList.contains("on")) close();
});
