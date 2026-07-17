import { useEffect, useState } from 'react'
import {
  assessEffectiveness,
  confirmExecution,
  deleteIntervention,
  getPdfUrl,
} from './api.js'
import ConfirmDialog from './ConfirmDialog.jsx'
import Dictate from './Dictate.jsx'
import Icon from './Icon.jsx'

// One row of the detail's "Acciones" card: tinted icon tile + label + trailing
// chevron, full width so the stack reads as a single aligned list (the card
// container draws the dividers with divide-y). Tones reuse the state-pill
// palette; full static class strings on purpose — Tailwind scans the source as
// text, so a `bg-${tone}` template would never be generated.
const TILE = {
  olive: 'bg-olive/10 text-olive',
  moss: 'bg-moss/12 text-moss',
  amber: 'bg-amber/12 text-amber',
  terra: 'bg-terra/10 text-terra',
}
const ROW_HOVER = {
  olive: 'hover:bg-olive/5',
  moss: 'hover:bg-moss/5',
  amber: 'hover:bg-amber/5',
  terra: 'hover:bg-terra/5',
}

// Renders an <a> when `href` is given (the ready PDF download must be a real
// anchor — see PdfButton), a <button> otherwise.
export function ActionRow({ icon, tone, label, danger = false, href, download, onClick, disabled }) {
  const className = `flex w-full items-center gap-3 py-3 text-sm font-semibold transition active:scale-[0.99] disabled:opacity-50 ${ROW_HOVER[tone]}`
  const body = (
    <>
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${TILE[tone]}`}>
        <Icon name={icon} className="h-4 w-4" strokeWidth={icon === 'star' ? 0 : 2} />
      </span>
      <span className={`flex-1 text-left ${danger ? 'text-terra' : 'text-soil'}`}>{label}</span>
      <Icon name="chevron-right" className="h-4 w-4 shrink-0 text-ink/40" />
    </>
  )
  if (href) {
    return (
      <a href={href} download={download} className={className}>
        {body}
      </a>
    )
  }
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={className}>
      {body}
    </button>
  )
}

const fieldClass =
  'mt-1 w-full rounded-xl border border-line bg-card px-3 py-2 text-sm text-soil outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15'

// Today's civil date (YYYY-MM-DD) in Spain — the confirm form prefills the
// application date with it (CLAUDE.md rule 9: dates are decided in the advisor's
// timezone, not UTC). 'en-CA' formats as YYYY-MM-DD.
const madridDay = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' })

// Downloads a record's prescription PDF in TWO steps, on purpose:
//   1. Tap "Preparar" -> sign the URL on demand, then fetch the PDF into memory
//      and wrap it in a blob: URL (all async).
//   2. Tap the resulting real <a> -> the browser downloads it.
// The split matters on mobile: a programmatic click or a location change fired
// AFTER the await is outside the user gesture and gets ignored, so nothing
// downloads. A genuine tap on a ready <a> is a native gesture the browser
// always honours.
// We fetch into a blob: URL instead of linking straight to the signed OSS URL
// because that URL is cross-origin: there the `download` attribute is ignored,
// and mobile browsers silently swallow a same-tab navigation to a cross-origin
// attachment (works on desktop, does nothing on phones). A blob: URL is
// same-origin, so `download` is honoured and the file saves reliably without
// leaving the PWA. (Requires CORS on the OSS bucket, since we now fetch it.)
export function PdfButton({ interventionId }) {
  const [status, setStatus] = useState('idle') // idle | loading | ready | error
  const [url, setUrl] = useState(null)

  async function prepare() {
    setStatus('loading')
    try {
      const signed = await getPdfUrl(interventionId)
      const res = await fetch(signed)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setUrl(URL.createObjectURL(await res.blob()))
      setStatus('ready')
    } catch (err) {
      console.error(err)
      setStatus('error')
    }
  }

  // Free the blob: URL on unmount so we don't leak memory.
  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])

  if (status === 'ready') {
    return (
      <ActionRow
        icon="download"
        tone="olive"
        label="Descargar prescripción (PDF)"
        href={url}
        download="prescripcion.pdf"
      />
    )
  }

  return (
    <ActionRow
      icon={status === 'error' ? 'refresh' : 'prescription'}
      tone="olive"
      onClick={prepare}
      disabled={status === 'loading'}
      label={
        status === 'loading'
          ? 'Preparando…'
          : status === 'error'
            ? 'No se pudo preparar — reintentar'
            : 'Preparar prescripción (PDF)'
      }
    />
  )
}

// Confirms a PRESCRIBED record as EXECUTED (FLUJO B). Collapsed it is a single
// link; expanded it asks for the REAL application date — prefilled to today as
// the device sees it (Europe/Madrid), editable because the treatment may have
// been applied days earlier (hard rule 2) — plus the optional real figures the
// record needs (dose and area, re-validated against the legal caps; spray
// volume; and who applied). On success the parent decides what to refresh.
export function ConfirmExecution({ interventionId, onConfirmed }) {
  const [open, setOpen] = useState(false)
  const [day, setDay] = useState(() => madridDay.format(new Date()))
  const [dose, setDose] = useState('')
  const [area, setArea] = useState('')
  const [spray, setSpray] = useState('')
  const [operator, setOperator] = useState('')
  const [operatorRopo, setOperatorRopo] = useState('')
  const [deliveryNote, setDeliveryNote] = useState('')
  const [status, setStatus] = useState('idle') // idle | saving | error
  const [error, setError] = useState('')

  async function submit() {
    setStatus('saving')
    setError('')
    try {
      // Noon UTC: the calendar day the advisor picked stays the same day both in
      // UTC (the backend's earliest_harvest = treatment_date.date()) and in
      // Madrid, with no midnight roll when converting the date-only value.
      const treatmentDate = new Date(`${day}T12:00:00Z`).toISOString()
      const updated = await confirmExecution(interventionId, {
        treatmentDate,
        appliedDose: dose,
        treatedAreaHa: area,
        sprayVolumeLHa: spray,
        operatorName: operator,
        operatorRopo,
        deliveryNoteNumber: deliveryNote,
      })
      onConfirmed(updated)
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  if (!open) {
    return (
      <ActionRow
        icon="check-circle"
        tone="moss"
        label="Confirmar ejecución"
        onClick={() => setOpen(true)}
      />
    )
  }

  return (
    <div className="flex flex-col gap-2 py-3">
      <p className="text-sm font-bold text-soil">Confirmar ejecución</p>
      <label className="text-xs font-semibold text-ink">
        Fecha de aplicación
        <input type="date" value={day} onChange={(e) => setDay(e.target.value)} className={fieldClass} />
      </label>
      <label className="text-xs font-semibold text-ink">
        Dosis real (opcional)
        <input
          type="number"
          inputMode="decimal"
          value={dose}
          onChange={(e) => setDose(e.target.value)}
          placeholder="la prescrita"
          className={fieldClass}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        Superficie tratada en ha (opcional)
        <input
          type="number"
          inputMode="decimal"
          value={area}
          onChange={(e) => setArea(e.target.value)}
          className={fieldClass}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        Caldo en L/ha (opcional)
        <input
          type="number"
          inputMode="decimal"
          value={spray}
          onChange={(e) => setSpray(e.target.value)}
          className={fieldClass}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        Aplicador (opcional)
        <input
          type="text"
          value={operator}
          onChange={(e) => setOperator(e.target.value)}
          placeholder="el titular por defecto"
          className={fieldClass}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        ROPO del aplicador (opcional)
        <input
          type="text"
          value={operatorRopo}
          onChange={(e) => setOperatorRopo(e.target.value)}
          className={fieldClass}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        Nº albarán/factura (opcional)
        <input
          type="text"
          value={deliveryNote}
          onChange={(e) => setDeliveryNote(e.target.value)}
          placeholder="el del producto aplicado"
          className={fieldClass}
        />
      </label>
      {status === 'error' && <p className="text-xs text-terra">{error}</p>}
      <div className="mt-1 flex items-center gap-4">
        <button
          type="button"
          onClick={submit}
          disabled={status === 'saving'}
          className="rounded-xl bg-moss px-4 py-2 text-xs font-bold text-white shadow-card transition hover:brightness-95 active:scale-[0.97] disabled:opacity-50"
        >
          {status === 'saving' ? 'Confirmando…' : 'Confirmar'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          disabled={status === 'saving'}
          className="text-xs font-semibold text-ink hover:underline"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

// Soft-deletes the record (M8.2) behind an in-app confirm dialog — destructive,
// so the extra tap is deliberate. The backend never removes the row (hard rule
// 1): it just stops being visible in the app. On success the parent leaves the
// screen, since the record no longer exists for the UI.
export function DeleteRecord({ interventionId, onDeleted }) {
  const [confirming, setConfirming] = useState(false)
  const [status, setStatus] = useState('idle') // idle | deleting | error
  const [error, setError] = useState('')

  async function remove() {
    setConfirming(false)
    setStatus('deleting')
    setError('')
    try {
      await deleteIntervention(interventionId)
      onDeleted()
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  return (
    <div>
      <ActionRow
        icon="trash"
        tone="terra"
        danger
        label={status === 'deleting' ? 'Eliminando…' : 'Eliminar registro'}
        onClick={() => setConfirming(true)}
        disabled={status === 'deleting'}
      />
      {status === 'error' && <p className="pb-3 text-xs text-terra">{error}</p>}
      <ConfirmDialog
        open={confirming}
        title="¿Eliminar este registro?"
        body="Dejará de aparecer en el cuaderno de campo."
        confirmLabel="Eliminar"
        onConfirm={remove}
        onCancel={() => setConfirming(false)}
      />
    </div>
  )
}

// The three effectiveness ratings, English value -> Spanish label + colour. The
// backend validates the value against its enum, so these must match GOOD/FAIR/POOR.
const RATINGS = [
  { value: 'GOOD', label: 'Buena', className: 'bg-moss' },
  { value: 'FAIR', label: 'Regular', className: 'bg-amber' },
  { value: 'POOR', label: 'Mala', className: 'bg-terra' },
]

// Assesses an EXECUTED record's effectiveness (FLUJO C) -> ASSESSED. Collapsed it
// is a single link; expanded it asks for the rating (Buena/Regular/Mala), the
// date the advisor judged it (prefilled to today, editable — the assessment is
// days later), and an OPTIONAL reason the advisor can DICTATE: the mic records a
// short note, POST /api/transcribe turns it into text, and it lands in an
// editable box so the advisor reviews what Qwen heard before saving. On success
// the parent decides what to refresh.
export function AssessEffectiveness({ interventionId, onAssessed }) {
  const [open, setOpen] = useState(false)
  const [rating, setRating] = useState(null) // GOOD | FAIR | POOR
  const [day, setDay] = useState(() => madridDay.format(new Date()))
  const [notes, setNotes] = useState('')
  const [status, setStatus] = useState('idle') // idle | saving | error
  const [error, setError] = useState('')

  // Append a dictated fragment (with a space) so several dictations accumulate;
  // the advisor can still edit the box by hand afterwards.
  function appendNote(text) {
    setNotes((prev) => (prev ? `${prev} ${text}` : text))
  }

  async function submit() {
    if (!rating) {
      setError('Elige Buena, Regular o Mala.')
      setStatus('error')
      return
    }
    setStatus('saving')
    setError('')
    try {
      const updated = await assessEffectiveness(interventionId, {
        effectiveness: rating,
        effectivenessDate: day, // a plain YYYY-MM-DD; the column is a DATE
        effectivenessNotes: notes,
      })
      onAssessed(updated)
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  if (!open) {
    return (
      <ActionRow icon="star" tone="amber" label="Valorar eficacia" onClick={() => setOpen(true)} />
    )
  }

  return (
    <div className="flex flex-col gap-2 py-3">
      <p className="text-sm font-bold text-soil">Valorar eficacia</p>
      <span className="text-xs font-semibold text-ink">¿Cómo funcionó el tratamiento?</span>
      <div className="flex gap-2">
        {RATINGS.map((r) => (
          <button
            key={r.value}
            type="button"
            onClick={() => setRating(r.value)}
            className={`flex-1 rounded-lg py-1.5 text-xs font-bold transition ${
              rating === r.value
                ? `${r.className} text-white`
                : 'border border-line text-ink'
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      <label className="text-xs font-semibold text-ink">
        Fecha de la valoración
        <input type="date" value={day} onChange={(e) => setDay(e.target.value)} className={fieldClass} />
      </label>

      <label className="text-xs font-semibold text-ink">
        Motivo (opcional)
        <textarea
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Escríbelo o díctalo con el micrófono"
          className={fieldClass}
        />
      </label>
      <Dictate onTranscribed={appendNote} label="Dictar el motivo" />

      {status === 'error' && <p className="text-xs text-terra">{error}</p>}
      <div className="mt-1 flex items-center gap-4">
        <button
          type="button"
          onClick={submit}
          disabled={status === 'saving'}
          className="rounded-xl bg-amber px-4 py-2 text-xs font-bold text-white shadow-card transition hover:brightness-95 active:scale-[0.97] disabled:opacity-50"
        >
          {status === 'saving' ? 'Guardando…' : 'Guardar valoración'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          disabled={status === 'saving'}
          className="text-xs font-semibold text-ink hover:underline"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}
