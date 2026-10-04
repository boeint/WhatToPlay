// A small in-app confirmation dialog, used instead of the browser's confirm().
//   if (await confirmDialog("Discard changes?", "Discard")) { ... }

const overlay = document.getElementById("dialog");

let resolveCurrent = null;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function confirmDialog(message, okLabel = "OK", { danger = false } = {}) {
  overlay.innerHTML = `<div class="modal" role="dialog" aria-modal="true">
      <p class="dialog-text">${esc(message)}</p>
      <div class="roll-actions" style="justify-content:flex-end">
        <button type="button" class="btn-ghost" data-dialog="cancel">Cancel</button>
        <button type="button" class="${danger ? "btn-danger" : "btn-primary"}" data-dialog="ok">${esc(okLabel)}</button>
      </div>
    </div>`;
  overlay.classList.add("on");
  overlay.querySelector('[data-dialog="ok"]').focus();
  return new Promise((resolve) => { resolveCurrent = resolve; });
}

export const isDialogOpen = () => overlay.classList.contains("on");

function answer(value) {
  overlay.classList.remove("on");
  resolveCurrent?.(value);
  resolveCurrent = null;
}

overlay.addEventListener("click", (event) => {
  const button = event.target.closest("[data-dialog]");
  if (button) answer(button.dataset.dialog === "ok");
  else if (event.target === overlay) answer(false);   // click outside the box
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && isDialogOpen()) {
    event.stopImmediatePropagation();   // don't also close the panel underneath
    answer(false);
  }
}, true);
