import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listInterventions, getPdfUrl, confirmExecution } from './api.js'

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
function PdfButton({ interventionId }) {
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

// Spanish label + colour for each lifecycle state (from the brand palette).
const STATE_STYLE = {
  OBSERVATION: { label: 'Observación', className: 'bg-sky' },
  PRESCRIBED: { label: 'Prescripción', className: 'bg-olive' },
  EXECUTED: { label: 'Ejecución', className: 'bg-moss' },
  ASSESSED: { label: 'Evaluada', className: 'bg-amber' },
}

// The civil date (YYYY-MM-DD) of a UTC timestamp, AS SEEN in Spain. The backend
// stores UTC; "today" must be decided in the advisor's timezone (CLAUDE.md rule
// 9), so e.g. a record made at 00:30 Madrid still counts as today, not
// yesterday's UTC date. 'en-CA' formats as YYYY-MM-DD, easy to compare as text.
const madridDay = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' })
// HH:mm in Spain, shown on each row.
const madridTime = new Intl.DateTimeFormat('es-ES', {
  timeZone: 'Europe/Madrid',
  hour: '2-digit',
  minute: '2-digit',
})

// Compact weather line for an executed record. Skips any reading the provider
// left empty, so a partial response still shows what it has. Returns '' when
// there is nothing (e.g. a prescription, or weather still pending).
function weatherSummary(r) {
  const parts = []
  if (r.temperature_c != null) parts.push(`🌡️ ${Math.round(r.temperature_c)} °C`)
  if (r.relative_humidity_pct != null) parts.push(`💧 ${Math.round(r.relative_humidity_pct)} %`)
  if (r.wind_speed_kmh != null) {
    parts.push(`💨 ${Math.round(r.wind_speed_kmh)} km/h ${r.wind_direction ?? ''}`.trim())
  }
  return parts.join(' · ')
}

// Confirms a PRESCRIBED record as EXECUTED (FLUJO B). Collapsed it is a single
// link; expanded it asks for the REAL application date — prefilled to today as
// the device sees it (Europe/Madrid), editable because the treatment may have
// been applied days earlier (hard rule 2) — plus the optional real figures the
// record needs (dose and area, re-validated against the legal caps; spray
// volume; and who applied). On success the parent swaps the row for the
// returned EXECUTED record.
function ConfirmExecution({ interventionId, onConfirmed }) {
  const [open, setOpen] = useState(false)
  const [day, setDay] = useState(() => madridDay.format(new Date()))
  const [dose, setDose] = useState('')
  const [area, setArea] = useState('')
  const [spray, setSpray] = useState('')
  const [operator, setOperator] = useState('')
  const [operatorRopo, setOperatorRopo] = useState('')
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
        className="mt-2 text-xs font-semibold text-moss underline"
      >
        ✅ Confirmar ejecución
      </button>
    )
  }

  const field = 'mt-1 w-full rounded-lg border border-line px-2 py-1 text-sm text-soil'
  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
      <label className="text-xs font-semibold text-ink">
        Fecha de aplicación
        <input type="date" value={day} onChange={(e) => setDay(e.target.value)} className={field} />
      </label>
      <label className="text-xs font-semibold text-ink">
        Dosis real (opcional)
        <input
          type="number"
          inputMode="decimal"
          value={dose}
          onChange={(e) => setDose(e.target.value)}
          placeholder="la prescrita"
          className={field}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        Superficie tratada en ha (opcional)
        <input
          type="number"
          inputMode="decimal"
          value={area}
          onChange={(e) => setArea(e.target.value)}
          className={field}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        Caldo en L/ha (opcional)
        <input
          type="number"
          inputMode="decimal"
          value={spray}
          onChange={(e) => setSpray(e.target.value)}
          className={field}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        Aplicador (opcional)
        <input
          type="text"
          value={operator}
          onChange={(e) => setOperator(e.target.value)}
          placeholder="el titular por defecto"
          className={field}
        />
      </label>
      <label className="text-xs font-semibold text-ink">
        ROPO del aplicador (opcional)
        <input
          type="text"
          value={operatorRopo}
          onChange={(e) => setOperatorRopo(e.target.value)}
          className={field}
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

// The advisor's records made TODAY. Re-fetches whenever `refreshKey` changes
// (the parent bumps it after a new recording is saved).
function TodayList({ refreshKey }) {
  const navigate = useNavigate()
  const [records, setRecords] = useState([])
  // Starts at 'loading' so the first mount shows "Cargando…" without us having
  // to setState synchronously inside the effect.
  const [status, setStatus] = useState('loading') // loading | ready | error
  // Bumped by the retry button to re-run the effect on demand.
  const [attempt, setAttempt] = useState(0)

  // Fetch today's records. The fetch lives INLINE in the effect (not in a
  // useCallback) so the linter can see that every setState is behind the
  // `await` — i.e. it runs asynchronously, never synchronously during the
  // effect, which would cascade renders. `active` guards against a late
  // response landing after the component unmounted or a newer fetch started.
  useEffect(() => {
    let active = true
    async function fetchToday() {
      try {
        const all = await listInterventions()
        if (!active) return
        const today = madridDay.format(new Date())
        // Keep only today's, ignoring any row without a timestamp just in case.
        setRecords(
          all.filter((r) => r.created_at && madridDay.format(new Date(r.created_at)) === today),
        )
        setStatus('ready')
      } catch (err) {
        if (!active) return
        console.error(err)
        setStatus('error')
      }
    }
    fetchToday()
    return () => {
      active = false
    }
    // refreshKey: a new record was saved. attempt: the retry button.
  }, [refreshKey, attempt])

  // Retry flips to 'loading' (allowed in an event handler) and re-runs the
  // effect by bumping `attempt`.
  function retry() {
    setStatus('loading')
    setAttempt((a) => a + 1)
  }

  if (status === 'loading') {
    return <p className="mt-6 text-center text-sm text-ink">Cargando…</p>
  }
  if (status === 'error') {
    return (
      <div className="mt-6 text-center">
        <p className="text-sm text-terra">No se pudo cargar la lista.</p>
        <button
          type="button"
          onClick={retry}
          className="mt-2 text-sm font-semibold text-olive underline"
        >
          Reintentar
        </button>
      </div>
    )
  }
  if (records.length === 0) {
    return (
      <p className="mt-6 text-center text-sm text-ink">
        Aún no hay registros hoy. Graba el primero.
      </p>
    )
  }

  return (
    <ul className="mt-4 flex flex-col gap-3">
      {records.map((r) => {
        const style = STATE_STYLE[r.lifecycle_state] ?? {
          label: r.lifecycle_state,
          className: 'bg-ink',
        }
        const weather = weatherSummary(r)
        return (
          <li key={r.id} className="rounded-xl border border-line bg-card p-4 shadow-sm">
            {/* Tapping the summary opens the detail; the action buttons below
                stay outside this region so they don't trigger navigation. */}
            <div
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/registro/${r.id}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  navigate(`/registro/${r.id}`)
                }
              }}
              className="cursor-pointer"
            >
            <div className="flex items-center justify-between">
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-bold text-white ${style.className}`}
              >
                {style.label}
              </span>
              <span className="text-xs text-ink">
                {madridTime.format(new Date(r.created_at))}
              </span>
            </div>

            {/* Observations carry free text; treatments carry product + dose. */}
            {r.observation ? (
              <p className="mt-2 text-sm leading-relaxed text-soil">{r.observation}</p>
            ) : (
              <div className="mt-2 text-sm text-soil">
                <p className="font-semibold">{r.product_registration_number}</p>
                <p className="text-ink">
                  {r.dose != null && `${r.dose} ${r.dose_unit ?? ''}`.trim()}
                  {r.target_pest && ` · ${r.target_pest}`}
                </p>
                {r.earliest_harvest_date && (
                  <p className="mt-1 text-xs text-ink">
                    Cosecha no antes de: {r.earliest_harvest_date}
                  </p>
                )}
                {/* Weather captured at execution; or a flag if it is still pending. */}
                {weather ? (
                  <p className="mt-1 text-xs text-ink">{weather}</p>
                ) : (
                  r.audit_state === 'WEATHER_PENDING' && (
                    <p className="mt-1 text-xs text-terra">⛅ Clima pendiente</p>
                  )
                )}
                {/* Non-blocking notice: the equipment's ITEAF inspection was
                    expired (or unrecorded) on the treatment day. */}
                {r.iteaf_warning && (
                  <p className="mt-1 text-xs font-semibold text-terra">
                    ⚠️ Inspección ITEAF caducada
                  </p>
                )}
              </div>
            )}
            </div>

            {r.has_pdf && <PdfButton interventionId={r.id} />}

            {/* A prescription can be confirmed as executed (FLUJO B). On success
                swap just this row for the returned EXECUTED record — no refetch. */}
            {r.lifecycle_state === 'PRESCRIBED' && (
              <ConfirmExecution
                interventionId={r.id}
                onConfirmed={(updated) =>
                  setRecords((rs) => rs.map((x) => (x.id === updated.id ? updated : x)))
                }
              />
            )}
          </li>
        )
      })}
    </ul>
  )
}

export default TodayList
