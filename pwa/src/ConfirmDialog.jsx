// In-app replacement for window.confirm on destructive actions: same
// two-step guarantee, but styled like the app — the native dialog looked
// foreign (and leaks the site URL in its title bar). Controlled by the parent:
// render with open=false and it draws nothing.
function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel }) {
  if (!open) return null
  return (
    /* Backdrop: dims the screen and cancels on tap outside the card. */
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onCancel}
      className="fixed inset-0 z-50 flex items-center justify-center bg-soil/40 px-6"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xs rounded-2xl bg-card p-5 shadow-float"
      >
        <p className="text-base font-bold text-soil">{title}</p>
        <p className="mt-1.5 text-sm leading-relaxed text-ink">{body}</p>
        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl border border-line bg-card py-2.5 text-sm font-semibold text-ink transition hover:bg-bone active:scale-[0.98]"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="flex-1 rounded-xl bg-terra py-2.5 text-sm font-bold text-white shadow-card transition hover:brightness-95 active:scale-[0.98]"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog
