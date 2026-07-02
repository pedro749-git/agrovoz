import { useEffect, useRef, useState } from 'react'
import {
  assessEffectiveness,
  confirmExecution,
  getPdfUrl,
  transcribeAudio,
} from './api.js'

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
      <a
        href={url}
        download="prescripcion.pdf"
        className="mt-2 inline-block text-xs font-semibold text-olive underline"
      >
        📄 Descargar prescripción (PDF)
      </a>
    )
  }

  return (
    <button
      type="button"
      onClick={prepare}
      className="mt-2 text-xs font-semibold text-olive underline"
    >
      {status === 'loading'
        ? 'Preparando…'
        : status === 'error'
          ? 'No se pudo preparar — reintentar'
          : '📄 Preparar prescripción (toca para generar PDF)'}
    </button>
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
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 text-sm font-semibold text-moss underline"
      >
        ✅ Confirmar ejecución
      </button>
    )
  }

  const fieldClass = 'mt-1 w-full rounded-lg border border-line px-2 py-1 text-sm text-soil'
  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
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
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={submit}
          disabled={status === 'saving'}
          className="rounded-lg bg-moss px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
        >
          {status === 'saving' ? 'Confirmando…' : 'Confirmar'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          disabled={status === 'saving'}
          className="text-xs font-semibold text-ink underline"
        >
          Cancelar
        </button>
      </div>
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
  // Dictation is its own little state machine, independent of the save.
  const [dictation, setDictation] = useState('idle') // idle | recording | transcribing | error
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  // Start capturing the reason. Mirrors Recorder: ask for the mic (needs HTTPS),
  // collect chunks, and on stop glue them into one blob and transcribe it.
  async function startDictation() {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop()) // release the mic
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        setDictation('transcribing')
        try {
          const text = await transcribeAudio(blob)
          // Append (with a space) so several dictations accumulate; the advisor
          // can still edit the box by hand afterwards.
          setNotes((prev) => (prev ? `${prev} ${text}` : text))
          setDictation('idle')
        } catch (err) {
          console.error(err)
          setDictation('error')
        }
      }
      recorder.start()
      setDictation('recording')
    } catch (err) {
      console.error(err)
      setError('No se pudo acceder al micrófono.')
      setDictation('error')
    }
  }

  function stopDictation() {
    mediaRecorderRef.current?.stop() // triggers onstop (transcription) above
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
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 text-sm font-semibold text-amber underline"
      >
        ★ Valorar eficacia
      </button>
    )
  }

  const fieldClass = 'mt-1 w-full rounded-lg border border-line px-2 py-1 text-sm text-soil'
  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
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
      <button
        type="button"
        onClick={dictation === 'recording' ? stopDictation : startDictation}
        disabled={dictation === 'transcribing'}
        className={`self-start text-xs font-semibold underline disabled:opacity-50 ${
          dictation === 'recording' ? 'text-terra' : 'text-olive'
        }`}
      >
        {dictation === 'recording'
          ? '⏹ Detener y transcribir'
          : dictation === 'transcribing'
            ? 'Transcribiendo…'
            : dictation === 'error'
              ? '🎤 Micrófono falló — reintentar'
              : '🎤 Dictar el motivo'}
      </button>

      {status === 'error' && <p className="text-xs text-terra">{error}</p>}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={submit}
          disabled={status === 'saving'}
          className="rounded-lg bg-amber px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
        >
          {status === 'saving' ? 'Guardando…' : 'Guardar valoración'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          disabled={status === 'saving'}
          className="text-xs font-semibold text-ink underline"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}
