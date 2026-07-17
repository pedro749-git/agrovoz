import { useEffect, useMemo } from 'react'
import Icon from './Icon.jsx'

// One queued take: the advisor can listen to it, retry it (Home feeds it back
// into the Recorder's preview → review → commit flow) or discard it. Discarding
// is legally fine — a pending take never reached the server, so it was never a
// record (hard rule 1 does not apply).
function PendingCard({ take, onRetry, onDiscard }) {
  // Blobs need an object URL to be playable; revoke it on cleanup or the audio
  // stays pinned in memory for the whole session.
  const url = useMemo(() => URL.createObjectURL(take.blob), [take])
  useEffect(() => () => URL.revokeObjectURL(url), [url])

  // When it was DICTATED (the future treatment_date, hard rule 2) — not when it
  // was queued or retried.
  const dictatedAt = new Date(take.deviceTimestamp).toLocaleString('es-ES', {
    dateStyle: 'short',
    timeStyle: 'short',
  })

  return (
    <div className="rounded-2xl border border-line bg-card p-4 shadow-card">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink">
        Dictada el {dictatedAt}
      </p>
      <audio controls src={url} className="mt-2 w-full" />
      <div className="mt-3 flex items-center gap-4">
        <button
          type="button"
          onClick={onRetry}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-olive py-2.5 text-sm font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98]"
        >
          <Icon name="refresh" className="h-4 w-4" />
          Reintentar
        </button>
        <button
          type="button"
          onClick={onDiscard}
          className="inline-flex items-center gap-1 text-xs font-semibold text-terra hover:underline"
        >
          <Icon name="trash" className="h-3.5 w-3.5" />
          Descartar
        </button>
      </div>
    </div>
  )
}

// Recordings queued while offline (see pendingTakes.js). Hidden when empty —
// the section only exists while there is a backlog to clear.
function PendingList({ takes, onRetry, onDiscard }) {
  if (takes.length === 0) return null

  return (
    <section className="mx-auto mt-10 w-full max-w-md">
      <h2 className="mb-1 text-xs font-bold uppercase tracking-[0.14em] text-amber">
        Pendientes de sincronizar
      </h2>
      <p className="mb-3 text-xs leading-relaxed text-ink">
        Grabaciones hechas sin conexión. Reintenta cuando tengas cobertura para
        revisarlas y guardarlas.
      </p>
      <div className="flex flex-col gap-3">
        {takes.map((take) => (
          <PendingCard
            key={take.transactionId}
            take={take}
            onRetry={() => onRetry(take)}
            onDiscard={() => onDiscard(take)}
          />
        ))}
      </div>
    </section>
  )
}

export default PendingList
