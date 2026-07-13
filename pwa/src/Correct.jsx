import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { correctIntervention, getIntervention } from './api.js'
import AppBar from './AppBar.jsx'
import ReviewForm from './ReviewForm.jsx'

// Correction screen (M8.2): reuses the M8.3 ReviewForm, but prefilled from an
// ALREADY-SAVED record instead of a fresh preview. On confirm the backend
// supersedes the record: it saves a NEW one with the edited fields (re-running
// the full legal validation) and soft-deletes the old one — a legal record is
// never edited in place (hard rules 1/7).

// The stored lifecycle state maps back to the form's record_type. An ASSESSED
// record was executed first, so its correction re-enters as an EXECUTION (the
// PWA only offers "Corregir" on OBSERVATION/PRESCRIBED for now, but the mapping
// stays total so a future slice doesn't crash on the others).
const STATE_TO_TYPE = {
  OBSERVATION: 'OBSERVATION',
  PRESCRIBED: 'PRESCRIPTION',
  EXECUTED: 'EXECUTION',
  ASSESSED: 'EXECUTION',
}

// Detail projection -> the ExtractedFields shape ReviewForm edits. Identities
// come from the nested context blocks (the record itself stores ids/the MAPA
// number, but commit resolves plot/product/equipment BY the names the advisor
// recognises). `dose` in the detail is already applied ?? prescribed.
function toFields(r) {
  return {
    record_type: STATE_TO_TYPE[r.lifecycle_state] ?? 'OBSERVATION',
    plot_alias: r.plot?.voice_alias ?? '',
    product_name: r.product?.trade_name ?? null,
    dose: r.dose,
    dose_unit: r.dose_unit,
    target_pest: r.target_pest,
    equipment_alias: r.equipment?.equipment_alias ?? null,
    observation: r.observation,
    spray_volume_l_ha: r.spray_volume_l_ha,
    treated_area_ha: r.treated_area_ha,
    justification: r.justification,
    previous_alternatives: r.previous_alternatives,
    operator_name: r.operator_name,
    operator_ropo: r.operator_ropo,
    planned_date: r.planned_date,
  }
}

// The ✓ markers under the identity fields. A saved record's identities WERE
// resolved against the catalog at commit, so they are honest "found" states —
// and the plot block carries the same crop/SIGPAC confidence line as a preview.
function toResolution(r) {
  return {
    plot: { found: !!r.plot, crop: r.plot?.crop, sigpac: r.plot?.sigpac },
    product: { found: !!r.product },
    equipment: { found: !!r.equipment },
  }
}

function Correct() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [r, setR] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | saving | error
  const [loadError, setLoadError] = useState('')
  const [saveError, setSaveError] = useState('')
  // The idempotency key for the REPLACEMENT record, captured once when the
  // screen mounts so a flaky-network retry reuses it (hard rule 3) instead of
  // creating two corrections.
  const [transactionId] = useState(() => crypto.randomUUID())

  useEffect(() => {
    let active = true
    getIntervention(id)
      .then((data) => {
        if (!active) return
        setR(data)
        setStatus('ready')
      })
      .catch((err) => {
        if (!active) return
        setLoadError(err.message)
        setStatus('error')
      })
    return () => {
      active = false
    }
  }, [id])

  // The old record is gone (soft-deleted); land on the replacement's detail.
  // `replace` so Back doesn't return to this form or the dead record.
  async function submit(fields) {
    setStatus('saving')
    setSaveError('')
    try {
      const saved = await correctIntervention(id, { fields, transactionId })
      navigate(`/registro/${saved.id}`, { replace: true })
    } catch (err) {
      // The backend's Spanish `mensaje` (a dose/area legal error, an unknown
      // product...) IS the feedback — shown in the form to fix and resubmit.
      setSaveError(err.message)
      setStatus('ready')
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <AppBar title="Corregir registro" onBack={() => navigate(-1)} />

      <main className="mx-auto w-full max-w-md flex-1 overflow-y-auto px-5 pb-safe">
        {status === 'loading' && (
          <p className="mt-6 text-center text-sm text-ink">Cargando…</p>
        )}
        {status === 'error' && (
          <p className="mt-6 text-center text-sm text-terra">{loadError}</p>
        )}
        {r && status !== 'loading' && status !== 'error' && (
          <>
            <p className="mt-4 text-xs leading-relaxed text-ink">
              El registro original no se pierde: se guarda uno corregido en su
              lugar y el antiguo queda anulado.
            </p>
            <div className="flex flex-col items-center">
              <ReviewForm
                transcription={r.raw_transcription ?? ''}
                fields={toFields(r)}
                resolution={toResolution(r)}
                onConfirm={submit}
                onCancel={() => navigate(-1)}
                submitting={status === 'saving'}
                error={saveError}
              />
            </div>
            <div className="h-8" />
          </>
        )}
      </main>
    </div>
  )
}

export default Correct
