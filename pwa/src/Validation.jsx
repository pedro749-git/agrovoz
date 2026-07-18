import { useEffect, useState } from 'react'
import {
  createValidation,
  getValidationPdfUrl,
  listHoldings,
} from './api.js'
import AppBar from './AppBar.jsx'
import BottomNav from './BottomNav.jsx'
import Dictate from './Dictate.jsx'
import Icon from './Icon.jsx'

// The two mandatory campaign validations, English value -> Spanish label. The
// backend validates the value against its enum, so these must match the model.
const TYPES = [
  { value: 'MID_CYCLE', label: 'Intermedia' },
  { value: 'FINAL', label: 'Final de campaña' },
]

// The current campaign is the civil year AS SEEN in Spain (CLAUDE.md rule 9): a
// signing at 00:30 Madrid on Jan 1st belongs to the new campaign, not the UTC
// year that may still be the old one. 'en-CA' gives YYYY-MM-DD; take the year.
const madridDay = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' })
const currentCampaign = () => madridDay.format(new Date()).slice(0, 4)

// dd/mm/yyyy for a plain YYYY-MM-DD (period bounds) or an ISO datetime.
function fmtDate(value) {
  if (!value) return '—'
  const [y, m, d] = value.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

// The validation screen (M7): the advisor's holdings, each with its plots and,
// per campaign, the two conformity slots to sign. Grouped by HOLDING because a
// validation covers the holding's records (rule 6), not a single plot's.
function Validation() {
  const [holdings, setHoldings] = useState([])
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    async function fetchHoldings() {
      try {
        const data = await listHoldings()
        if (!active) return
        setHoldings(data)
        setStatus('ready')
      } catch (err) {
        if (!active) return
        console.error(err)
        setStatus('error')
      }
    }
    fetchHoldings()
    return () => {
      active = false
    }
  }, [reload])

  const refresh = () => setReload((n) => n + 1)

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <AppBar title="Validaciones" subtitle="Conformidad de campaña" />

      <main className="mx-auto w-full max-w-md flex-1 overflow-y-auto px-5 pb-40">
        {status === 'loading' && (
          <p className="mt-6 text-center text-sm text-ink">Cargando…</p>
        )}
        {status === 'error' && (
          <div className="mt-6 text-center">
            <p className="text-sm text-terra">No se pudieron cargar las explotaciones.</p>
            <button
              type="button"
              onClick={refresh}
              className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-olive hover:underline"
            >
              <Icon name="refresh" className="h-4 w-4" />
              Reintentar
            </button>
          </div>
        )}
        {status === 'ready' && holdings.length === 0 && (
          <p className="mt-6 text-center text-sm text-ink">
            No tienes explotaciones asignadas.
          </p>
        )}
        {status === 'ready' && (
          <ul className="mt-4 flex flex-col gap-4">
            {holdings.map((h) => (
              <HoldingCard key={h.id} holding={h} onChanged={refresh} />
            ))}
          </ul>
        )}
      </main>

      <BottomNav />
    </div>
  )
}

// One holding: owner + REA/REGEPA, its plots, and a block per campaign. The
// campaigns shown are those that already have validations UNION the current one
// (so there is always somewhere to sign this campaign), newest first.
function HoldingCard({ holding, onChanged }) {
  const campaigns = [
    ...new Set([currentCampaign(), ...holding.validations.map((v) => v.campaign)]),
  ].sort((a, b) => b.localeCompare(a))

  return (
    <li className="rounded-2xl border border-line bg-card p-4 shadow-card">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-olive/10 text-olive">
          <Icon name="map-pin" className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="font-semibold text-soil">{holding.owner_name}</div>
          <div className="text-xs text-ink">REA/REGEPA: {holding.rea_regepa_number}</div>
          {holding.plots.length > 0 && (
            <div className="mt-0.5 text-xs text-ink">
              Parcelas: {holding.plots.map((p) => p.voice_alias).join(' · ')}
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {campaigns.map((campaign) => (
          <CampaignBlock
            key={campaign}
            holdingId={holding.id}
            campaign={campaign}
            validations={holding.validations.filter((v) => v.campaign === campaign)}
            onChanged={onChanged}
          />
        ))}
      </div>
    </li>
  )
}

// One campaign of a holding: the two slots (Intermedia / Final) with a 0/2..2/2
// counter. A present slot shows its verdict + PDF; a missing one offers to sign.
function CampaignBlock({ holdingId, campaign, validations, onChanged }) {
  const byType = Object.fromEntries(validations.map((v) => [v.type, v]))
  const done = TYPES.filter((t) => byType[t.value]).length

  return (
    <div className="rounded-xl border border-line bg-bone p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold text-soil">Campaña {campaign}</span>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${
            done === 2 ? 'bg-moss/12 text-moss' : 'bg-amber/12 text-amber'
          }`}
        >
          {done === 2 && <Icon name="check" className="h-3 w-3" />}
          {done}/2
        </span>
      </div>

      <div className="mt-2 flex flex-col gap-2">
        {TYPES.map((t) => (
          <Slot
            key={t.value}
            holdingId={holdingId}
            campaign={campaign}
            type={t}
            validation={byType[t.value]}
            onSigned={onChanged}
          />
        ))}
      </div>
    </div>
  )
}

// A single type slot: either the signed validation (verdict + date + PDF) or a
// sign form to create it.
function Slot({ holdingId, campaign, type, validation, onSigned }) {
  if (validation) {
    return (
      <div className="border-t border-line pt-2 first:border-t-0 first:pt-0">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-ink hover:underline">{type.label}</span>
          <span
            className={`inline-flex items-center gap-1 text-xs font-bold ${
              validation.conformity ? 'text-moss' : 'text-terra'
            }`}
          >
            <Icon
              name={validation.conformity ? 'check-circle' : 'alert-triangle'}
              className="h-3.5 w-3.5"
            />
            {validation.conformity ? 'Conforme' : 'No conforme'}
          </span>
        </div>
        <div className="text-xs text-ink">
          {fmtDate(validation.validation_date)} · {validation.intervention_count}{' '}
          intervenciones
        </div>
        {validation.remarks && (
          <div className="mt-0.5 text-xs italic text-ink">{validation.remarks}</div>
        )}
        {validation.has_pdf && <ValidationPdf validationId={validation.id} />}
      </div>
    )
  }
  return (
    <SignForm
      holdingId={holdingId}
      campaign={campaign}
      type={type}
      onSigned={onSigned}
    />
  )
}

// Signs one campaign validation. Collapsed it is a single link; expanded it asks
// for conformity (Sí/No) and optional remarks (the backend requires them when
// NOT conform). `validation_date` is the device clock — signed here and now.
function SignForm({ holdingId, campaign, type, onSigned }) {
  const [open, setOpen] = useState(false)
  const [conformity, setConformity] = useState(true)
  const [remarks, setRemarks] = useState('')
  const [status, setStatus] = useState('idle') // idle | saving | error
  const [error, setError] = useState('')

  async function submit() {
    setStatus('saving')
    setError('')
    try {
      await createValidation(holdingId, {
        campaign,
        validationType: type.value,
        conformity,
        validationDate: new Date().toISOString(), // device clock (hard rule 2)
        remarks,
      })
      onSigned()
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
        className="inline-flex items-center gap-1.5 self-start rounded-lg bg-olive/10 px-3 py-2 text-xs font-semibold text-olive transition hover:bg-olive/20 active:scale-[0.97]"
      >
        <Icon name="pen" className="h-4 w-4" />
        Firmar {type.label.toLowerCase()}
      </button>
    )
  }

  return (
    <div className="flex flex-col gap-2 border-t border-line pt-2">
      <span className="text-xs font-semibold text-ink hover:underline">
        Firmar validación «{type.label}»
      </span>
      <div className="flex gap-2">
        {[
          { value: true, label: 'Conforme', className: 'bg-moss' },
          { value: false, label: 'No conforme', className: 'bg-terra' },
        ].map((c) => (
          <button
            key={String(c.value)}
            type="button"
            onClick={() => setConformity(c.value)}
            className={`flex-1 rounded-xl py-2 text-xs font-bold transition ${
              conformity === c.value ? `${c.className} text-white` : 'border border-line text-ink hover:bg-olive/5'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <textarea
        rows={2}
        value={remarks}
        onChange={(e) => setRemarks(e.target.value)}
        placeholder={conformity ? 'Observaciones (opcional)' : 'Motivo (obligatorio si no conforme)'}
        className="w-full rounded-xl border border-line bg-card px-3 py-2 text-sm text-soil outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
      />
      <Dictate
        onTranscribed={(text) => setRemarks((prev) => (prev ? `${prev} ${text}` : text))}
        label="Dictar observaciones"
      />

      {status === 'error' && <p className="text-xs text-terra">{error}</p>}
      <div className="mt-1 flex items-center gap-4">
        <button
          type="button"
          onClick={submit}
          disabled={status === 'saving'}
          className="inline-flex items-center gap-1.5 rounded-xl bg-olive px-4 py-2 text-xs font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.97] disabled:opacity-50"
        >
          <Icon name="pen" className="h-3.5 w-3.5" />
          {status === 'saving' ? 'Firmando…' : 'Firmar y generar PDF'}
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

// Downloads the signed PDF. Mirrors PdfButton (RecordActions): fetch the signed
// URL, turn it into a same-origin blob: URL so `download` is honoured on phones.
function ValidationPdf({ validationId }) {
  const [status, setStatus] = useState('idle') // idle | loading | ready | error
  const [url, setUrl] = useState(null)

  async function prepare() {
    setStatus('loading')
    try {
      const signed = await getValidationPdfUrl(validationId)
      const res = await fetch(signed)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setUrl(URL.createObjectURL(await res.blob()))
      setStatus('ready')
    } catch (err) {
      console.error(err)
      setStatus('error')
    }
  }

  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])

  if (status === 'ready') {
    return (
      <a
        href={url}
        download="validacion.pdf"
        className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-olive/10 px-3 py-1.5 text-xs font-semibold text-olive"
      >
        <Icon name="download" className="h-4 w-4" />
        Descargar validación (PDF)
      </a>
    )
  }
  return (
    <button
      type="button"
      onClick={prepare}
      className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-olive/10 px-3 py-1.5 text-xs font-semibold text-olive transition hover:bg-olive/20 active:scale-[0.97]"
    >
      <Icon name={status === 'error' ? 'refresh' : 'download'} className="h-4 w-4" />
      {status === 'loading'
        ? 'Preparando…'
        : status === 'error'
          ? 'No se pudo preparar — reintentar'
          : 'Preparar validación (PDF)'}
    </button>
  )
}

export default Validation
