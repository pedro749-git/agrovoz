import { useState } from 'react'
import Icon from './Icon.jsx'

// Same field look as the other forms (RecordActions). Full static class string on
// purpose — Tailwind scans the source as text.
const fieldClass =
  'mt-1 w-full rounded-xl border border-line bg-card px-3 py-2 text-sm text-soil outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15'

// The LLM classifies the record; the advisor can correct it here. Values MUST
// match the backend's ExtractedFields.record_type literals.
const TYPES = [
  { value: 'OBSERVATION', label: 'Observación' },
  { value: 'PRESCRIPTION', label: 'Prescripción' },
  { value: 'EXECUTION', label: 'Ejecución' },
]

// One-line resolution marker under an identity field: green when preview matched
// a catalog row, terracotta with a fix-it hint when it didn't. `detail` overrides
// the "found" text (the plot shows its crop + SIGPAC there for confidence).
function FieldStatus({ found, detail, missLabel }) {
  if (found) {
    return (
      <p className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-moss">
        <Icon name="check-circle" className="h-3.5 w-3.5 shrink-0" />
        {detail ?? 'En el catálogo'}
      </p>
    )
  }
  return (
    <p className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-terra">
      <Icon name="alert-triangle" className="h-3.5 w-3.5 shrink-0" />
      {missLabel}
    </p>
  )
}

// Turns the edited form back into an ExtractedFields payload: numbers coerced,
// blank optionals -> null. Fields not shown in the form (previous_alternatives,
// planned_date, operator_*) ride along from the initial spread, so no value the
// LLM extracted is lost on commit even if it isn't editable in this slice.
function buildPayload(form) {
  const num = (v) => (v === '' || v == null ? null : Number(v))
  const str = (v) => (v == null || String(v).trim() === '' ? null : v)
  return {
    ...form,
    record_type: form.record_type,
    plot_alias: form.plot_alias ?? '',
    product_name: str(form.product_name),
    dose: num(form.dose),
    dose_unit: str(form.dose_unit),
    target_pest: str(form.target_pest),
    equipment_alias: str(form.equipment_alias),
    observation: str(form.observation),
    spray_volume_l_ha: num(form.spray_volume_l_ha),
    treated_area_ha: num(form.treated_area_ha),
    justification: str(form.justification),
    previous_alternatives: str(form.previous_alternatives),
    operator_name: str(form.operator_name),
    operator_ropo: str(form.operator_ropo),
    planned_date: str(form.planned_date),
  }
}

// Editable review of what the LLM extracted (M8, hard rule 4). Prefilled from
// `fields`, shown after preview and BEFORE commit: the advisor corrects any
// mis-heard value and on confirm the corrected ExtractedFields go to commit. The
// original transcription is shown read-only as "lo que dictaste" for reference —
// it is stored verbatim as the audit trail regardless of the edits.
function ReviewForm({ transcription, fields, resolution, onConfirm, onCancel, submitting, error }) {
  const [form, setForm] = useState(() => ({ ...fields }))
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const isTreatment = form.record_type !== 'OBSERVATION'
  // A resolution marker reflects the PREVIEW snapshot, so show it only while the
  // field is untouched; once the advisor edits the value, commit is the authority
  // (it re-resolves and 422s if the new value doesn't match).
  const unchanged = (key) => (form[key] ?? '') === (fields[key] ?? '')
  const plotDetail = [resolution?.plot?.crop, resolution?.plot?.sigpac && `SIGPAC ${resolution.plot.sigpac}`]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="mt-8 w-full max-w-xs rounded-2xl border border-line bg-card p-4 shadow-card">
      <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-ink">
        Revisa antes de guardar
      </p>

      {/* What Qwen heard, read-only, for reference. */}
      <p className="mb-3 rounded-lg bg-bone px-3 py-2 text-xs italic leading-relaxed text-ink">
        «{transcription}»
      </p>

      <span className="text-xs font-semibold text-ink">Tipo de registro</span>
      <div className="mb-2 mt-1 flex gap-1.5">
        {TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => setForm((f) => ({ ...f, record_type: t.value }))}
            className={`flex-1 rounded-lg py-1.5 text-[11px] font-bold transition ${
              form.record_type === t.value
                ? 'bg-olive text-white'
                : 'border border-line text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <label className="block text-xs font-semibold text-ink">
        Parcela
        <input
          type="text"
          value={form.plot_alias ?? ''}
          onChange={set('plot_alias')}
          className={fieldClass}
        />
      </label>
      {unchanged('plot_alias') && (
        <FieldStatus
          found={resolution?.plot?.found}
          detail={plotDetail || undefined}
          missLabel="No encuentro esa parcela — revísala"
        />
      )}

      {isTreatment ? (
        <>
          <label className="mt-2 block text-xs font-semibold text-ink">
            Producto
            <input
              type="text"
              value={form.product_name ?? ''}
              onChange={set('product_name')}
              className={fieldClass}
            />
          </label>
          {unchanged('product_name') && (
            <FieldStatus
              found={resolution?.product?.found}
              missLabel="No encuentro ese producto en el vademécum — revísalo"
            />
          )}
          <div className="mt-2 flex gap-2">
            <label className="flex-1 text-xs font-semibold text-ink">
              Dosis
              <input
                type="number"
                inputMode="decimal"
                value={form.dose ?? ''}
                onChange={set('dose')}
                className={fieldClass}
              />
            </label>
            <label className="flex-1 text-xs font-semibold text-ink">
              Unidad
              <input
                type="text"
                value={form.dose_unit ?? ''}
                onChange={set('dose_unit')}
                placeholder="L/ha"
                className={fieldClass}
              />
            </label>
          </div>
          <label className="mt-2 block text-xs font-semibold text-ink">
            Plaga objetivo
            <input
              type="text"
              value={form.target_pest ?? ''}
              onChange={set('target_pest')}
              className={fieldClass}
            />
          </label>
          <label className="mt-2 block text-xs font-semibold text-ink">
            Equipo
            <input
              type="text"
              value={form.equipment_alias ?? ''}
              onChange={set('equipment_alias')}
              className={fieldClass}
            />
          </label>
          {unchanged('equipment_alias') && (
            <FieldStatus
              found={resolution?.equipment?.found}
              missLabel="No encuentro ese equipo — revísalo"
            />
          )}
          <label className="mt-2 block text-xs font-semibold text-ink">
            Superficie tratada en ha (opcional)
            <input
              type="number"
              inputMode="decimal"
              value={form.treated_area_ha ?? ''}
              onChange={set('treated_area_ha')}
              className={fieldClass}
            />
          </label>
          <label className="mt-2 block text-xs font-semibold text-ink">
            Justificación (opcional)
            <textarea
              rows={2}
              value={form.justification ?? ''}
              onChange={set('justification')}
              className={fieldClass}
            />
          </label>
        </>
      ) : (
        <label className="mt-2 block text-xs font-semibold text-ink">
          Observación
          <textarea
            rows={3}
            value={form.observation ?? ''}
            onChange={set('observation')}
            className={fieldClass}
          />
        </label>
      )}

      {error && (
        <p className="mt-3 flex items-start gap-1.5 text-xs text-terra">
          <Icon name="alert-triangle" className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </p>
      )}

      <div className="mt-4 flex items-center gap-4">
        <button
          type="button"
          onClick={() => onConfirm(buildPayload(form))}
          disabled={submitting}
          className="rounded-xl bg-olive px-4 py-2.5 text-sm font-bold text-white shadow-card transition active:scale-[0.98] disabled:opacity-60"
        >
          {submitting ? 'Guardando…' : 'Confirmar y guardar'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="text-xs font-semibold text-ink"
        >
          Descartar
        </button>
      </div>
    </div>
  )
}

export default ReviewForm
