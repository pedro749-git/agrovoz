import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getIntervention } from './api.js'
import { PdfButton, ConfirmExecution } from './RecordActions.jsx'

// Spanish label + icon + colour per lifecycle state (inspired by the prototype).
const STATE = {
  OBSERVATION: { label: 'Observación', icon: '👁', className: 'bg-sky' },
  PRESCRIBED: { label: 'Prescripción', icon: '📄', className: 'bg-olive' },
  EXECUTED: { label: 'Ejecución', icon: '✓', className: 'bg-moss' },
  ASSESSED: { label: 'Evaluada', icon: '★', className: 'bg-amber' },
}

// Date-only strings (YYYY-MM-DD) are shown verbatim as DD/MM/YYYY — never parsed
// through Date(), which would treat them as UTC midnight and could roll back a
// day in Europe/Madrid. Datetimes ARE rendered in Madrid (CLAUDE.md rule 9).
const madridDateTime = new Intl.DateTimeFormat('es-ES', {
  timeZone: 'Europe/Madrid',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})
function fmtDateOnly(iso) {
  if (!iso) return null
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}
function fmtDateTime(iso) {
  return iso ? madridDateTime.format(new Date(iso)) : null
}

// One label/value line; renders nothing when the value is empty.
function KV({ k, v }) {
  if (v == null || v === '') return null
  return (
    <div className="flex justify-between gap-3 border-b border-line py-2 text-sm last:border-none">
      <span className="text-ink">{k}</span>
      <span className="max-w-[62%] text-right font-semibold text-soil">{v}</span>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <>
      <h3 className="mt-5 mb-2 text-[10px] font-bold uppercase tracking-wider text-ink">
        {title}
      </h3>
      <div className="rounded-xl border border-line bg-card p-3">{children}</div>
    </>
  )
}

// The three-cell weather strip, shown only when there is at least one reading.
function Weather({ r }) {
  const cells = []
  if (r.temperature_c != null) cells.push([`${Math.round(r.temperature_c)}°`, 'Temp'])
  if (r.relative_humidity_pct != null) {
    cells.push([`${Math.round(r.relative_humidity_pct)}%`, 'Humedad'])
  }
  if (r.wind_speed_kmh != null) {
    cells.push([`${Math.round(r.wind_speed_kmh)}`, `km/h ${r.wind_direction ?? ''}`.trim()])
  }
  if (cells.length === 0) {
    return r.audit_state === 'WEATHER_PENDING' ? (
      <p className="text-xs text-terra">⛅ Clima pendiente</p>
    ) : null
  }
  return (
    <div className="flex gap-2">
      {cells.map(([val, lab]) => (
        <div key={lab} className="flex-1 rounded-lg bg-bone py-2 text-center">
          <div className="text-sm font-bold text-soil">{val}</div>
          <div className="mt-0.5 text-[8.5px] uppercase tracking-wide text-ink">{lab}</div>
        </div>
      ))}
    </div>
  )
}

function Detail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [r, setR] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [error, setError] = useState('')
  // Bumped after a successful execution confirm to re-fetch the FULL detail:
  // the confirm endpoint returns the lean list projection, so re-loading here
  // keeps the rich context blocks (plot/holding/transcription) intact.
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const data = await getIntervention(id)
        if (!active) return
        setR(data)
        setStatus('ready')
      } catch (err) {
        if (!active) return
        setError(err.message)
        setStatus('error')
      }
    }
    load()
    return () => {
      active = false
    }
  }, [id, reloadKey])

  const s = r ? (STATE[r.lifecycle_state] ?? STATE.OBSERVATION) : null

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <header className="flex items-center gap-3 bg-olive-d px-4 pb-3 pt-safe text-white">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="pt-3 text-lg leading-none"
          aria-label="Volver"
        >
          ‹
        </button>
        <div className="pt-3 text-sm font-semibold">{s ? s.label : 'Registro'}</div>
      </header>

      <main className="mx-auto w-full max-w-md flex-1 overflow-y-auto px-5 pb-safe">
        {status === 'loading' && (
          <p className="mt-6 text-center text-sm text-ink">Cargando…</p>
        )}
        {status === 'error' && (
          <p className="mt-6 text-center text-sm text-terra">{error}</p>
        )}
        {status === 'ready' && r && (
          <>
            {/* Hero: state + plot context (the where). */}
            <div className="pt-5 text-center">
              <div
                className={`mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-2xl text-2xl text-white ${s.className}`}
              >
                {s.icon}
              </div>
              <div className="text-lg font-bold">{r.plot?.voice_alias ?? '—'}</div>
              {r.plot && (
                <div className="mt-0.5 text-xs text-ink">
                  {[r.plot.crop, r.plot.variety, r.plot.enclosure_area_ha != null && `${r.plot.enclosure_area_ha} ha`]
                    .filter(Boolean)
                    .join(' · ')}
                </div>
              )}
              <div className="mt-1 text-xs text-ink">
                {fmtDateTime(r.treatment_date || r.prescription_date || r.created_at)}
              </div>
            </div>

            {/* OBSERVATION */}
            {r.lifecycle_state === 'OBSERVATION' && (
              <Section title="Lo que observé">
                <KV k="Plaga vigilada" v={r.target_pest} />
                {r.observation && (
                  <p className="mt-2 border-l-2 border-sky bg-bone px-3 py-2 text-sm italic text-soil">
                    «{r.observation}»
                  </p>
                )}
              </Section>
            )}

            {/* PRESCRIPTION */}
            {r.lifecycle_state === 'PRESCRIBED' && (
              <Section title="Tratamiento prescrito">
                <KV k="Producto (nº MAPA)" v={r.product_registration_number} />
                <KV
                  k="Dosis"
                  v={r.prescribed_dose != null && `${r.prescribed_dose} ${r.dose_unit ?? ''}`.trim()}
                />
                <KV k="Plaga objetivo" v={r.target_pest} />
                <KV k="Fecha prevista" v={fmtDateOnly(r.planned_date)} />
                <KV k="Justificación" v={r.justification} />
                <KV k="Alternativas previas" v={r.previous_alternatives} />
              </Section>
            )}

            {/* EXECUTION */}
            {r.lifecycle_state === 'EXECUTED' && (
              <Section title="Aplicación real">
                <KV k="Producto (nº MAPA)" v={r.product_registration_number} />
                <KV
                  k="Dosis aplicada"
                  v={r.applied_dose != null && `${r.applied_dose} ${r.dose_unit ?? ''}`.trim()}
                />
                <KV k="Caldo" v={r.spray_volume_l_ha != null && `${r.spray_volume_l_ha} L/ha`} />
                <KV k="Sup. tratada" v={r.treated_area_ha != null && `${r.treated_area_ha} ha`} />
                <KV k="Plaga objetivo" v={r.target_pest} />
                <KV
                  k="Aplicador"
                  v={[r.operator_name, r.operator_ropo].filter(Boolean).join(' · ') || null}
                />
                <KV
                  k="Maquinaria"
                  v={
                    r.equipment
                      ? [r.equipment.equipment_alias, r.equipment.roma_number].filter(Boolean).join(' · ')
                      : null
                  }
                />
                <KV k="Nº albarán" v={r.delivery_note_number} />
                <KV k="Cosecha desde" v={fmtDateOnly(r.earliest_harvest_date)} />
              </Section>
            )}

            {r.iteaf_warning && (
              <p className="mt-3 rounded-lg bg-amber/20 px-3 py-2 text-xs font-semibold text-terra">
                ⚠️ Inspección ITEAF caducada
              </p>
            )}

            {/* Weather, only when captured (execution). */}
            {(r.temperature_c != null || r.audit_state === 'WEATHER_PENDING') && (
              <Section title="Condiciones (fecha real)">
                <Weather r={r} />
              </Section>
            )}

            {/* The owner the record legally belongs to. */}
            {r.holding && (
              <Section title="Titular">
                <KV k="Explotación" v={r.holding.owner_name} />
                <KV k="REA/REGEPA" v={r.holding.rea_regepa_number} />
                <KV k="SIGPAC" v={r.plot?.sigpac} />
              </Section>
            )}

            {/* What the advisor dictated (the audio itself is not stored yet). */}
            {r.raw_transcription && (
              <Section title="Lo que dictaste">
                <p className="text-sm italic leading-relaxed text-soil">
                  «{r.raw_transcription}»
                </p>
              </Section>
            )}

            {/* Actions live here now (moved off the list row). The PDF download
                for prescriptions, and confirming a prescription's execution. */}
            <div className="mt-6 flex flex-col border-t border-line pt-3">
              {r.has_pdf && <PdfButton interventionId={r.id} />}
              {r.lifecycle_state === 'PRESCRIBED' && (
                <ConfirmExecution
                  interventionId={r.id}
                  // Re-fetch the full detail so the promoted EXECUTED record keeps
                  // its rich context (the confirm response is the lean projection).
                  onConfirmed={() => setReloadKey((k) => k + 1)}
                />
              )}
            </div>

            <div className="h-8" />
          </>
        )}
      </main>
    </div>
  )
}

export default Detail
