import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listInterventions } from './api.js'

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
        // The whole row is a summary; tapping it opens the detail, where the
        // PDF download and confirm-execution actions now live.
        return (
          <li
            key={r.id}
            role="button"
            tabIndex={0}
            onClick={() => navigate(`/registro/${r.id}`)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                navigate(`/registro/${r.id}`)
              }
            }}
            className="cursor-pointer rounded-xl border border-line bg-card p-4 shadow-sm"
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
          </li>
        )
      })}
    </ul>
  )
}

export default TodayList
