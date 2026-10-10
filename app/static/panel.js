// Game detail panel: every field of one game, saved together with "Save".
// Fields use name="..." (not data-field), so the table's save-on-change
// listener in app.js ignores them.
import { api } from "./api.js";
import { confirmDialog } from "./dialog.js";

const panel = document.getElementById("panel");
const backdrop = document.getElementById("backdrop");

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const STATUSES = [["unplayed", "Unplayed"], ["playing", "Playing"], ["finished", "Finished"], ["skip", "Skip"]];

// { mode: "edit" | "create", game, franchise, franchises, platforms, onSave, onDelete }
let current = null;

// What a new game starts as, in create mode.
export const BLANK_GAME = {
  id: null, title: "", release_year: null, release_month: null, release_tba: false,
  status: "unplayed", finished_on: null, length_hours: null, notes: "", platforms: [], play_on: null,
  links: [], backloggd_url: null, backloggd_link: "",
};

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// Same rule as the backend's format_release(), for the live preview.
function releaseLabel(year, month, tba) {
  const label = month && year ? `${MONTHS[month - 1]} ${year}` : year ? String(year) : "";
  if (tba) return label ? `${label} (TBA)` : "TBA";
  return label || "—";
}

const linkRow = (link = { label: "", url: "" }) => `<div class="link-row">
    <input name="link-label" placeholder="Label" value="${esc(link.label)}" maxlength="100">
    <input name="link-url" type="url" placeholder="https://…" value="${esc(link.url)}">
    <button type="button" class="del" data-panel="remove-link" title="Remove link">×</button>
  </div>`;

function render() {
  const { game: g, franchise, franchises, platforms, mode } = current;
  const creating = mode === "create";
  const monthOptions = `<option value="">—</option>` +
    MONTHS.map((m, i) => `<option value="${i + 1}" ${g.release_month === i + 1 ? "selected" : ""}>${m}</option>`).join("");
  const statusChoices = STATUSES.map(([value, label]) => `<label>
      <input type="radio" name="status" value="${value}" ${g.status === value ? "checked" : ""}>
      <span class="${value}">${label}</span></label>`).join("");
  const platformChecks = platforms.map((p) => `<label>
      <input type="checkbox" name="platform" value="${esc(p.name)}" ${g.platforms.includes(p.name) ? "checked" : ""}><span>${esc(p.name)}</span></label>`).join("");
  const franchiseOptions = [...franchises].sort((a, b) => a.name.localeCompare(b.name)).map((f) =>
    `<option value="${f.id}" ${f.id === franchise.id ? "selected" : ""}>${esc(f.name)}</option>`).join("");

  panel.innerHTML = `
    <div class="panel-head">
      <div class="kicker">${creating ? "New game in " : ""}${esc(franchise.name)}</div>
      <input name="title" value="${esc(g.title)}" maxlength="255" aria-label="Title" placeholder="Title">
    </div>
    <div class="panel-body">
      <div class="field">
        <span class="label">Release (full launch)</span>
        <div class="row">
          <input name="release_year" type="number" min="1950" max="2100" placeholder="Year" value="${g.release_year ?? ""}" aria-label="Release year">
          <select name="release_month" aria-label="Release month">${monthOptions}</select>
          <label class="check"><input type="checkbox" name="release_tba" ${g.release_tba ? "checked" : ""}> TBA</label>
        </div>
        <div class="hint">Shows as: <b data-out="release"></b></div>
      </div>

      <div class="field">
        <span class="label">Status</span>
        <div class="statuses">${statusChoices}</div>
        <div class="row" data-show="finished" style="margin-top:10px">
          <label class="check">Finished on <input type="date" name="finished_on" value="${g.finished_on ?? ""}"></label>
        </div>
      </div>

      <div class="field">
        <label for="length_hours">Length (main story)</label>
        <div class="row">
          <input name="length_hours" id="length_hours" type="number" min="1" max="999" step="1"
                 placeholder="Hours" value="${g.length_hours ?? ""}"> hours
          <button type="button" class="lnkbtn" data-panel="lookup-length">Look up on HowLongToBeat</button>
        </div>
        <div data-out="length-matches"></div>
        <div class="hint">As on HowLongToBeat ("Main Story"). Used by the picker's length filter.</div>
      </div>

      <div class="field">
        <span class="label">Available on</span>
        <div class="toggles">${platformChecks}</div>
      </div>

      <div class="field">
        <label for="play_on">Play on</label>
        <select name="play_on" id="play_on"></select>
      </div>

      <div class="field">
        <label for="notes">Notes</label>
        <textarea name="notes" id="notes">${esc(g.notes)}</textarea>
      </div>

      <div class="field">
        <span class="label">Links</span>
        <div data-out="links">${g.links.map(linkRow).join("")}</div>
        <button type="button" class="lnkbtn" data-panel="add-link">＋ Add link</button>
      </div>

      <div class="field">
        <label for="backloggd_url">Backloggd page</label>
        <input name="backloggd_url" id="backloggd_url" type="url" value="${esc(g.backloggd_url)}"
               placeholder="Leave empty to use the automatic link">
        <div class="hint">${g.backloggd_link
          ? `Opens: <a href="${esc(g.backloggd_link)}" target="_blank" rel="noopener">${esc(g.backloggd_link)}</a>`
          : "Empty: the link is generated from the title."}</div>
      </div>

      <div class="field">
        <label for="franchise_id">Franchise</label>
        <select name="franchise_id" id="franchise_id">${franchiseOptions}</select>
        <div class="hint">${creating ? "The game is added at the end of this franchise."
                                     : "Moving a game puts it at the end of the other franchise."}</div>
      </div>
    </div>
    <div class="panel-foot">
      ${creating ? "" : `<button type="button" class="del-game" data-panel="delete">Delete</button>`}
      <span class="panel-error" data-out="error" role="alert"></span>
      <button type="button" class="btn-ghost" data-panel="close">Cancel</button>
      <button type="button" class="btn-primary" data-panel="save">${creating ? "Create" : "Save"}</button>
    </div>`;
  refreshDependentFields();
}

// Parts of the form that depend on other fields.
function refreshDependentFields() {
  const form = (name) => panel.querySelector(`[name="${name}"]`);
  const year = Number(form("release_year").value) || null;
  const month = Number(form("release_month").value) || null;
  panel.querySelector('[data-out="release"]').textContent = releaseLabel(year, month, form("release_tba").checked);

  const status = panel.querySelector('[name="status"]:checked').value;
  panel.querySelector('[data-show="finished"]').hidden = status !== "finished";

  // "Play on" offers only the platforms currently ticked.
  const ticked = [...panel.querySelectorAll('[name="platform"]:checked')].map((c) => c.value);
  const select = form("play_on");
  const chosen = select.options.length ? select.value : (current.game.play_on ?? "");
  select.innerHTML = `<option value="">—</option>` + ticked.map((p) =>
    `<option ${p === chosen ? "selected" : ""}>${esc(p)}</option>`).join("");
  select.disabled = ticked.length === 0;
}

// ---------- length lookup ----------
// HowLongToBeat's best matches for the title as typed; picking one fills the Length field.
async function lookupLength(button) {
  const out = panel.querySelector('[data-out="length-matches"]');
  const title = panel.querySelector('[name="title"]').value.trim();
  if (!title) return (out.textContent = "Type the title first.");
  const year = Number(panel.querySelector('[name="release_year"]').value) || null;
  button.disabled = true;
  out.textContent = "Looking up…";
  try {
    const { matches } = await api.lookupLength(title, year);
    const usable = matches.filter((m) => m.hours);
    out.innerHTML = usable.length
      ? `<div class="length-matches">${usable.map((m) => `<div class="length-match">
          <button type="button" class="btn-ghost" data-panel="use-length" data-hours="${m.hours}">Use ${m.hours} h</button>
          <a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.name)}${m.year ? ` (${m.year})` : ""}</a>
          <span class="hint">${m.main_story} h · ${m.players} player${m.players === 1 ? "" : "s"}</span>
        </div>`).join("")}</div>`
      : "No main-story time found on HowLongToBeat.";
  } catch (err) {
    out.textContent = err.message;
  } finally {
    button.disabled = false;
  }
}

// ---------- reading the form ----------
// The form's values, in the same shape the API uses.
function readForm() {
  const field = (name) => panel.querySelector(`[name="${name}"]`);
  const status = panel.querySelector('[name="status"]:checked').value;
  const links = [...panel.querySelectorAll(".link-row")]
    .map((row) => ({
      label: row.querySelector('[name="link-label"]').value.trim(),
      url: row.querySelector('[name="link-url"]').value.trim(),
    }))
    .filter((link) => link.label || link.url)                 // ignore fully empty rows
    .map((link) => ({ label: link.label || "link", url: link.url }));
  return {
    title: field("title").value.trim(),
    release_year: Number(field("release_year").value) || null,
    release_month: Number(field("release_month").value) || null,
    release_tba: field("release_tba").checked,
    status,
    finished_on: status === "finished" ? field("finished_on").value || null : null,
    length_hours: field("length_hours").value === "" ? null : Number(field("length_hours").value),
    platforms: [...panel.querySelectorAll('[name="platform"]:checked')].map((c) => c.value),
    play_on: field("play_on").value || null,
    notes: field("notes").value,
    links,
    backloggd_url: field("backloggd_url").value.trim() || null,
    franchise_id: Number(field("franchise_id").value),
  };
}

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// Only the fields that differ from the game as loaded.
function changedFields() {
  const g = current.game;
  const form = readForm();
  const before = {
    ...g,
    // The form lists platforms in the standard order; compare in that order too,
    // so an unchanged set doesn't count as a change.
    platforms: current.platforms.map((p) => p.name).filter((name) => g.platforms.includes(name)),
    links: g.links.map(({ label, url }) => ({ label, url })),
    franchise_id: current.franchise.id,
  };
  const changes = {};
  for (const [key, value] of Object.entries(form)) {
    if (!same(value, before[key] ?? null)) changes[key] = value;
  }
  // Becoming finished with no date given: let the server set today's date.
  if (form.status === "finished" && g.status !== "finished" && form.finished_on === null) {
    delete changes.finished_on;
  }
  // Leaving "finished": the server clears the date itself.
  if (form.status !== "finished") delete changes.finished_on;
  return changes;
}

// Mistakes we can spot without asking the server.
function problems(form) {
  if (!form.title) return "The title can't be empty.";
  if (form.release_month && !form.release_year) return "A release month needs a year.";
  if (form.length_hours !== null && !(Number.isInteger(form.length_hours) && form.length_hours >= 1 && form.length_hours <= 999))
    return "The length must be a whole number of hours, from 1 to 999.";
  if (form.links.some((link) => !link.url)) return "Each link needs a URL.";
  if (form.links.some((link) => !/^https?:\/\//.test(link.url))) return "Links must start with http:// or https://";
  if (form.backloggd_url && !/^https?:\/\//.test(form.backloggd_url)) return "The Backloggd page must start with http:// or https://";
  return null;
}

function showError(message) {
  panel.querySelector('[data-out="error"]').textContent = message;
}

async function save(button) {
  const problem = problems(readForm());
  if (problem) return showError(problem);
  const changes = changedFields();
  if (!Object.keys(changes).length) return closePanel();   // nothing to save
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Saving…";
  try {
    await current.onSave(current.game.id, changes);   // id is null when creating
    closePanel();
  } catch (err) {
    showError(`Not saved: ${err.message}`);   // keep the panel open with what was typed
    button.disabled = false;
    button.textContent = label;
  }
}

async function remove() {
  const { game, onDelete } = current;
  if (!(await confirmDialog(`Delete "${game.title}"?`, "Delete", { danger: true }))) return;
  try {
    await onDelete(game.id);
    closePanel();
  } catch (err) {
    showError(`Not deleted: ${err.message}`);
  }
}

// ---------- opening / closing ----------
export function openGamePanel(options) {
  current = options;
  render();
  panel.hidden = false;
  backdrop.hidden = false;
  panel.querySelector('[name="title"]').focus();
}

export function closePanel() {
  panel.hidden = true;
  backdrop.hidden = true;
  current = null;
}

// Cancel / Esc / click outside: ask first if there are unsaved changes.
async function requestClose() {
  if (Object.keys(changedFields()).length &&
      !(await confirmDialog("Discard your unsaved changes?", "Discard", { danger: true }))) return;
  closePanel();
}

export const isPanelOpen = () => !panel.hidden;

// ---------- listeners (set up once) ----------
panel.addEventListener("input", refreshDependentFields);
panel.addEventListener("change", refreshDependentFields);

panel.addEventListener("click", (event) => {
  const button = event.target.closest("[data-panel]");
  if (!button) return;
  const action = button.dataset.panel;
  if (action === "close") requestClose();
  else if (action === "add-link") {
    panel.querySelector('[data-out="links"]').insertAdjacentHTML("beforeend", linkRow());
    panel.querySelector('[data-out="links"] .link-row:last-child input').focus();
  } else if (action === "remove-link") button.closest(".link-row").remove();
  else if (action === "lookup-length") lookupLength(button);
  else if (action === "use-length") {
    panel.querySelector('[name="length_hours"]').value = button.dataset.hours;
    panel.querySelector('[data-out="length-matches"]').textContent = "";
  } else if (action === "save") save(button);
  else if (action === "delete") remove();
});

// Ctrl+Enter (Cmd+Enter on a Mac) saves from anywhere in the panel.
panel.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) save(panel.querySelector('[data-panel="save"]'));
});

backdrop.addEventListener("click", requestClose);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && isPanelOpen()) requestClose();
});
