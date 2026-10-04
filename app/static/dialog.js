// Small in-app dialogs, used instead of the browser's confirm() / prompt().
//   if (await confirmDialog("Discard changes?", "Discard")) { ... }
//   await formDialog({ title, body, okLabel, onSubmit: async (form) => { ... } })

const overlay = document.getElementById("dialog");

let resolveCurrent = null;
let submitCurrent = null;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function open(html, resolve, onSubmit = null) {
  overlay.innerHTML = `<form class="modal" role="dialog" aria-modal="true" novalidate>${html}</form>`;
  overlay.classList.add("on");
  resolveCurrent = resolve;
  submitCurrent = onSubmit;
  (overlay.querySelector("input, textarea, select") || overlay.querySelector('[data-dialog="ok"]')).focus();
}

function close(value) {
  overlay.classList.remove("on");
  resolveCurrent?.(value);
  resolveCurrent = submitCurrent = null;
}

const buttons = (okLabel, danger) => `<p class="dialog-error" data-out="error" role="alert"></p>
  <div class="roll-actions" style="justify-content:flex-end">
    <button type="button" class="btn-ghost" data-dialog="cancel">Cancel</button>
    <button type="submit" class="${danger ? "btn-danger" : "btn-primary"}" data-dialog="ok">${esc(okLabel)}</button>
  </div>`;

// Yes / no question. Resolves to true or false.
export function confirmDialog(message, okLabel = "OK", { danger = false } = {}) {
  return new Promise((resolve) =>
    open(`<p class="dialog-text">${esc(message)}</p>${buttons(okLabel, danger)}`, resolve));
}

// A small form. onSubmit(form) may throw: the message is shown and the dialog
// stays open. Resolves to true when submitted, false when cancelled.
export function formDialog({ title, body, okLabel = "OK", danger = false, onSubmit }) {
  return new Promise((resolve) =>
    open(`<h2 style="font-size:18px">${esc(title)}</h2>${body}${buttons(okLabel, danger)}`, resolve, onSubmit));
}

export const isDialogOpen = () => overlay.classList.contains("on");

overlay.addEventListener("click", (event) => {
  if (event.target.closest('[data-dialog="cancel"]')) close(false);
  else if (event.target === overlay) close(false);   // click outside the box
});

overlay.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!submitCurrent) return close(true);
  const okButton = overlay.querySelector('[data-dialog="ok"]');
  okButton.disabled = true;
  try {
    await submitCurrent(event.target);
    close(true);
  } catch (err) {
    overlay.querySelector('[data-out="error"]').textContent = err.message;
    okButton.disabled = false;
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && isDialogOpen()) {
    event.stopImmediatePropagation();   // don't also close the panel underneath
    close(false);
  }
}, true);
