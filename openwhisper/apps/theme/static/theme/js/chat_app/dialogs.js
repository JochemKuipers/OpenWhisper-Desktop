export function openDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.showModal === "function") {
    if (!dialog.open) dialog.showModal();
    return;
  }
  dialog.classList.remove("hidden");
}

export function closeDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.close === "function") {
    if (dialog.open) dialog.close();
    return;
  }
  dialog.classList.add("hidden");
}

export function isDialogOpen(dialog) {
  if (!dialog) return false;
  if (typeof dialog.open === "boolean") return dialog.open;
  return !dialog.classList.contains("hidden");
}

export function wireDialogDismiss(dialog, closeButtons) {
  if (!dialog) return;
  (closeButtons || []).forEach(function (btn) {
    if (!btn) return;
    btn.addEventListener("click", function () {
      closeDialog(dialog);
    });
  });
  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) closeDialog(dialog);
  });
}
