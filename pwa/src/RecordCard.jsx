import { useNavigate } from 'react-router-dom'
import Icon from './Icon.jsx'

// One record as a tappable summary card. Shared by the Home "today" list and the
// history screen so both render a record identically; tapping opens the detail,
// where the PDF download and the confirm/assess actions live.

// Spanish label + brand colour for each lifecycle state. `dot`/`text`/`tint`
// drive the tinted status pill (soft background + coloured text + a solid dot),
// which reads lighter than a fully filled badge.
const STATE_STYLE = {
  OBSERVATION: { label: 'Observación', dot: 'bg-sky', text: 'text-sky', tint: 'bg-sky/10' },
  PRESCRIBED: { label: 'Prescripción', dot: 'bg-olive', text: 'text-olive', tint: 'bg-olive/10' },
  EXECUTED: { label: 'Ejecución', dot: 'bg-moss', text: 'text-moss', tint: 'bg-moss/12' },
  ASSESSED: { label: 'Evaluada', dot: 'bg-amber', text: 'text-amber', tint: 'bg-amber/12' },
}

// HH:mm in Spain, shown on each row (rule 9: render Europe/Madrid).
const madridTime = new Intl.DateTimeFormat('es-ES', {
  timeZone: 'Europe/Madrid',
  hour: '2-digit',
  minute: '2-digit',
})

// Compact weather readings for an executed record, as {icon, text} cells so they
// render with SVG icons instead of emoji. Skips any reading the provider left
// empty, so a partial response still shows what it has. Returns [] when there is
// nothing (e.g. a prescription, or weather still pending).
function weatherCells(r) {
  const cells = []
  if (r.temperature_c != null) {
    cells.push({ icon: 'thermometer', text: `${Math.round(r.temperature_c)} °C` })
  }
  if (r.relative_humidity_pct != null) {
    cells.push({ icon: 'droplet', text: `${Math.round(r.relative_humidity_pct)} %` })
  }
  if (r.wind_speed_kmh != null) {
    cells.push({
      icon: 'wind',
      text: `${Math.round(r.wind_speed_kmh)} km/h ${r.wind_direction ?? ''}`.trim(),
    })
  }
  return cells
}

function RecordCard({ record: r }) {
  const navigate = useNavigate()
  const style = STATE_STYLE[r.lifecycle_state] ?? {
    label: r.lifecycle_state,
    dot: 'bg-ink',
    text: 'text-ink',
    tint: 'bg-ink/10',
  }
  const weather = weatherCells(r)
  // "Finca de Pepe · José Ruiz": which plot and whose holding, so cards from
  // different fincas tell apart at a glance. Skips whatever is missing.
  const context = [r.plot_alias, r.holding_owner_name].filter(Boolean).join(' · ')

  return (
    <li
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/registro/${r.id}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          navigate(`/registro/${r.id}`)
        }
      }}
      className="cursor-pointer rounded-2xl border border-line bg-card p-4 shadow-card transition hover:border-olive/40 active:scale-[0.99]"
    >
      <div className="flex items-center justify-between">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${style.tint} ${style.text}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
          {style.label}
        </span>
        <span className="text-xs tabular-nums text-ink">
          {madridTime.format(new Date(r.created_at))}
        </span>
      </div>

      {context && (
        <p className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-ink">
          <Icon name="leaf" className="h-3.5 w-3.5" />
          {context}
        </p>
      )}

      {/* Observations carry free text; treatments carry product + dose. Snug
          under the context line when there is one, normal gap otherwise. */}
      {r.observation ? (
        <p className={`${context ? 'mt-1' : 'mt-2.5'} text-sm leading-relaxed text-soil`}>
          {r.observation}
        </p>
      ) : (
        <div className={`${context ? 'mt-1' : 'mt-2.5'} text-sm text-soil`}>
          {/* Trade name the advisor recognises; MAPA number as fallback when
              the product is not in the catalog. */}
          <p className="font-semibold text-olive-d">
            {r.product_trade_name ?? r.product_registration_number}
          </p>
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
          {weather.length > 0 ? (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink">
              {weather.map((c) => (
                <span key={c.icon} className="inline-flex items-center gap-1">
                  <Icon name={c.icon} className="h-3.5 w-3.5" />
                  {c.text}
                </span>
              ))}
            </div>
          ) : (
            r.audit_state === 'WEATHER_PENDING' && (
              <p className="mt-1.5 inline-flex items-center gap-1 text-xs text-amber">
                <Icon name="cloud" className="h-3.5 w-3.5" />
                Clima pendiente
              </p>
            )
          )}
          {/* Non-blocking notice: the equipment's ITEAF inspection was expired
              (or unrecorded) on the treatment day. */}
          {r.iteaf_warning && (
            <p className="mt-1.5 inline-flex items-center gap-1 text-xs font-semibold text-terra">
              <Icon name="alert-triangle" className="h-3.5 w-3.5" />
              Inspección ITEAF caducada
            </p>
          )}
        </div>
      )}
    </li>
  )
}

export default RecordCard
