// Game detail panel: every field of one game, saved together with "Save".
// Fields use name="..." (not data-field), so the table's save-on-change
// listener in app.js ignores them.

const panel = document.getElementById("panel");
const backdrop = document.getElementById("backdrop");

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const STATUSES = [["unplayed", "Unplayed"], ["playing", "Playing"], ["finished", "Finished"], ["skip", "Skip"]];

let current = null;   // { game, franchise, franchises, platforms, onSave }

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
  const { game: g, franchise, franchises, platforms } = current;
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
      <div class="kicker">${esc(franchise.name)}</div>
      <input name="title" value="${esc(g.title)}" maxlength="255" aria-label="Title">
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
        <div class="hint">Opens: <a href="${esc(g.backloggd_link)}" target="_blank" rel="noopener">${esc(g.backloggd_link)}</a></div>
      </div>

      <div class="field">
        <label for="franchise_id">Franchise</label>
        <select name="franchise_id" id="franchise_id">${franchiseOptions}</select>
        <div class="hint">Moving a game puts it at the end of the other franchise.</div>
      </div>
    </div>
    <div class="panel-foot">
      <button type="button" class="btn-ghost" data-panel="close">Cancel</button>
      <button type="button" class="btn-primary" data-panel="save">Save</button>
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

export const isPanelOpen = () => !panel.hidden;

// ---------- listeners (set up once) ----------
panel.addEventListener("input", refreshDependentFields);
panel.addEventListener("change", refreshDependentFields);

panel.addEventListener("click", (event) => {
  const button = event.target.closest("[data-panel]");
  if (!button) return;
  const action = button.dataset.panel;
  if (action === "close") closePanel();
  else if (action === "add-link") {
    panel.querySelector('[data-out="links"]').insertAdjacentHTML("beforeend", linkRow());
    panel.querySelector('[data-out="links"] .link-row:last-child input').focus();
  } else if (action === "remove-link") button.closest(".link-row").remove();
  else if (action === "save") {
    button.textContent = "Saving comes in the next step";
  }
});

backdrop.addEventListener("click", closePanel);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && isPanelOpen()) closePanel();
});
