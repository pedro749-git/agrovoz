import { useEffect, useMemo, useState } from 'react'
import { listInterventions } from './api.js'
import AppBar from './AppBar.jsx'
import BottomNav from './BottomNav.jsx'
import Icon from './Icon.jsx'
import RecordCard from './RecordCard.jsx'

// Civil dates AS SEEN in Spain (rule 9): the range the advisor picks is in their
// own timezone; the backend maps it to a UTC window. 'en-CA' gives YYYY-MM-DD.
const madridDay = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' })

// Shift a civil date by whole days. Anchored at noon UTC so a ±day step never
// lands on a DST boundary and rolls the civil date; re-formatted back in Madrid.
function shiftDays(dateStr, delta) {
  const d = new Date(`${dateStr}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + delta)
  return madridDay.format(d)
}

// The full history with a date filter. Defaults to the current month (a bounded,
// fast query) rather than all-time; "Todo" removes the bounds. The same
// /api/interventions endpoint powers this and the Home "today" list — only the
// range differs.
function History() {
  // Presets, computed once against today's Madrid date. `from`/`to` are civil
  // dates; '' means an open end (so "Todo" is from '' to '').
  const { today, presets } = useMemo(() => {
    const t = madridDay.format(new Date())
    return {
      today: t,
      presets: [
        { key: 'month', label: 'Este mes', from: `${t.slice(0, 7)}-01`, to: t },
        { key: '30d', label: 'Últimos 30 días', from: shiftDays(t, -29), to: t },
        { key: 'all', label: 'Todo', from: '', to: '' },
      ],
    }
  }, [])

  // The range is the source of truth; the active preset is derived by matching.
  const [from, setFrom] = useState(presets[0].from)
  const [to, setTo] = useState(presets[0].to)
  const [records, setRecords] = useState([])
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [attempt, setAttempt] = useState(0)

  const activePreset = presets.find((p) => p.from === from && p.to === to)?.key ?? null

  // Every range change shows the spinner (set here, in the event handler, not in
  // the effect — a synchronous setState inside an effect cascades renders). The
  // first load needs none: `status` already starts at 'loading'.
  function applyPreset(p) {
    setStatus('loading')
    setFrom(p.from)
    setTo(p.to)
  }

  useEffect(() => {
    let active = true
    async function fetchRange() {
      try {
        const data = await listInterventions({ from: from || undefined, to: to || undefined })
        if (!active) return
        setRecords(data)
        setStatus('ready')
      } catch (err) {
        if (!active) return
        console.error(err)
        setStatus('error')
      }
    }
    fetchRange()
    return () => {
      active = false
    }
  }, [from, to, attempt])

  const inputClass =
    'w-full rounded-xl border border-line bg-card px-3 py-2 text-sm text-soil outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15'

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <AppBar title="Historial" />

      <main className="mx-auto w-full max-w-md flex-1 overflow-y-auto px-5 pb-40">
        {/* Filter panel: quick presets + a manual from/to range. */}
        <section className="mt-4 rounded-2xl border border-line bg-card p-4 shadow-card">
          <div className="flex flex-wrap gap-2">
            {presets.map((p) => (
              <button
                key={p.key}
                type="button"
                onClick={() => applyPreset(p)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                  activePreset === p.key
                    ? 'bg-olive text-white'
                    : 'bg-olive/10 text-olive hover:bg-olive/20 active:scale-[0.97]'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="mt-3 flex items-end gap-2">
            <label className="flex-1 text-[11px] font-semibold text-ink">
              Desde
              <input
                type="date"
                value={from}
                max={to || today}
                onChange={(e) => {
                  setStatus('loading')
                  setFrom(e.target.value)
                }}
                className={`mt-1 ${inputClass}`}
              />
            </label>
            <label className="flex-1 text-[11px] font-semibold text-ink">
              Hasta
              <input
                type="date"
                value={to}
                min={from || undefined}
                max={today}
                onChange={(e) => {
                  setStatus('loading')
                  setTo(e.target.value)
                }}
                className={`mt-1 ${inputClass}`}
              />
            </label>
          </div>
        </section>

        {status === 'loading' && <p className="mt-6 text-center text-sm text-ink">Cargando…</p>}
        {status === 'error' && (
          <div className="mt-6 text-center">
            <p className="text-sm text-terra">No se pudo cargar el historial.</p>
            <button
              type="button"
              onClick={() => {
                setStatus('loading')
                setAttempt((a) => a + 1)
              }}
              className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-olive hover:underline"
            >
              <Icon name="refresh" className="h-4 w-4" />
              Reintentar
            </button>
          </div>
        )}
        {status === 'ready' && (
          <>
            <p className="mt-4 px-1 text-xs text-ink">
              {records.length === 0
                ? 'Sin registros en este periodo'
                : `${records.length} ${records.length === 1 ? 'registro' : 'registros'}`}
            </p>
            {records.length === 0 ? (
              <div className="mt-6 flex flex-col items-center text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-olive/10 text-olive">
                  <Icon name="calendar" className="h-7 w-7" />
                </div>
                <p className="mt-3 max-w-[16rem] text-sm text-ink">
                  Prueba a ampliar el rango de fechas o pulsa «Todo».
                </p>
              </div>
            ) : (
              <ul className="mt-2 flex flex-col gap-3 pb-8">
                {records.map((r) => (
                  <RecordCard key={r.id} record={r} />
                ))}
              </ul>
            )}
          </>
        )}
      </main>

      <BottomNav />
    </div>
  )
}

export default History
