import { supabase } from './supabase.js'

// Thin client over the backend's two PWA endpoints. Every call is authenticated
// with the advisor's Supabase access token (JWT). Requests are same-origin
// (`/api/...`): in dev the Vite proxy forwards them to the FastAPI server, so
// there is no CORS to configure and it works through the cloudflared tunnel too.

// Reads the current access token from the stored session. Throws if there is
// none — both endpoints require an authenticated advisor.
async function authHeader() {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new Error('No hay sesión activa. Vuelve a iniciar sesión.')
  return { Authorization: `Bearer ${token}` }
}

// Turns the backend's {error, mensaje} shape into a thrown Error carrying the
// Spanish message, so callers can show `err.message` straight to the advisor.
// The machine-readable code ("DOSE_ERROR", ...) rides along as `err.code` so
// the UI can style legal-validation blocks differently from plain errors.
async function unwrap(response) {
  if (response.ok) return response.json()
  let mensaje = 'Error inesperado. Inténtalo de nuevo.'
  let code = null
  try {
    const body = await response.json()
    if (body?.mensaje) mensaje = body.mensaje
    if (body?.error) code = body.error
  } catch {
    // Non-JSON error body (e.g. a proxy 502): keep the generic message.
  }
  const error = new Error(mensaje)
  error.code = code
  throw error
}

// fetch() rejects (with a TypeError) only when the request never got an HTTP
// answer at all: offline, DNS failure, connection dropped mid-flight. That is
// the one case where the recorder queues the audio locally instead of showing
// an error, so we tag it with `isNetwork`. An HTTP 4xx/5xx is NOT that case —
// the server answered (e.g. a 422 dose block) and its Spanish `mensaje` must
// surface through unwrap() as always. Only the two recording calls use this;
// elsewhere a network failure is just an error to show.
async function fetchTaggingOffline(url, options) {
  try {
    return await fetch(url, options)
  } catch {
    const offline = new Error('Sin conexión con el servidor.')
    offline.isNetwork = true
    throw offline
  }
}

// POST /api/records/preview — phase 1 (M8): uploads one audio note and gets back
// the transcription + extracted fields, WITHOUT persisting. The advisor reviews
// and corrects them before committing (hard rule 4: nothing from the LLM reaches
// the legal record unseen). Side-effect free, so it carries no idempotency key —
// a failed preview is simply retried.
export async function previewRecord(audioBlob) {
  const form = new FormData()
  // A filename lets the backend infer the audio type (MediaRecorder gives webm).
  form.append('audio', audioBlob, 'note.webm')

  const response = await fetchTaggingOffline('/api/records/preview', {
    method: 'POST',
    // NOTE: do not set Content-Type — the browser sets it WITH the multipart
    // boundary. Setting it by hand would corrupt the upload.
    headers: await authHeader(),
    body: form,
  })
  return unwrap(response) // { transcription, fields }
}

// POST /api/records — phase 2 (M8): persists the advisor-REVIEWED fields,
// returning the saved record (or a 4xx whose `mensaje` we surface, e.g. a
// dose/area legal error the advisor fixes and resubmits). JSON body, not
// FormData: `fields` is a nested object (ExtractedFields) that form-encoding
// can't carry.
//
// `transactionId` and `deviceTimestamp` were captured when the recording STOPPED
// and are reused on retry:
//   - transactionId (crypto.randomUUID) is the idempotency key (hard rule 3): a
//     flaky-network retry hits the existing row instead of duplicating a record.
//   - deviceTimestamp is the device clock (hard rule 2): the treatment date is
//     when the advisor spoke in the field, never when the server received it.
// `transcription` is the ORIGINAL audio transcription, stored as the audit trail
// regardless of what the advisor edited.
export async function commitRecord({ fields, transactionId, deviceTimestamp, transcription }) {
  const response = await fetchTaggingOffline('/api/records', {
    method: 'POST',
    headers: { ...(await authHeader()), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fields,
      transaction_id: transactionId,
      device_timestamp: deviceTimestamp,
      transcription,
    }),
  })
  return unwrap(response)
}

// POST /api/bootstrap — provisions the demo advisor + sandbox for a user who
// just self-signed-up (hackathon only, TEMPORARY). Idempotent: safe to call on
// every "just signed up" render. The backend 404s this when the hackathon flag
// is off, so callers should only reach it through the signup path.
export async function bootstrap() {
  const response = await fetch('/api/bootstrap', {
    method: 'POST',
    headers: await authHeader(),
  })
  return unwrap(response)
}

// GET /api/interventions — the advisor's records, newest first. Optional `from`
// and `to` are civil dates (YYYY-MM-DD) AS SEEN IN SPAIN, both inclusive: the
// Home list asks for today (from == to), the history screen for a wider span.
// The backend maps them to the exact UTC window, so the client sends plain
// Madrid dates and never juggles timezones itself.
export async function listInterventions({ from, to } = {}) {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const query = params.toString()
  const response = await fetch(`/api/interventions${query ? `?${query}` : ''}`, {
    headers: await authHeader(),
  })
  return unwrap(response)
}

// PATCH /api/interventions/:id/execution — confirms a PRESCRIBED record as
// EXECUTED with the real application data (FLUJO B). Only `treatmentDate` is
// required: the PWA prefills it with the device date but it is editable, since
// the treatment may have been applied days before it is confirmed (hard rule 2).
// The optional fields (appliedDose, treatedAreaHa, sprayVolumeLHa, operatorName,
// operatorRopo, deliveryNoteNumber) are sent only when the advisor types them; when omitted the
// backend falls back to the prescribed dose / holding default operator and
// re-validates legality with whatever real values arrive. Form-encoded to match
// the backend endpoint (Form(...)), like the other write endpoints.
export async function confirmExecution(
  interventionId,
  {
    treatmentDate,
    appliedDose,
    treatedAreaHa,
    sprayVolumeLHa,
    operatorName,
    operatorRopo,
    deliveryNoteNumber,
  },
) {
  const form = new FormData()
  form.append('treatment_date', treatmentDate)
  // Optional fields: send only when the advisor typed one, so an empty box keeps
  // the backend's fallback (prescribed dose / holding default operator).
  const optional = {
    applied_dose: appliedDose,
    treated_area_ha: treatedAreaHa,
    spray_volume_l_ha: sprayVolumeLHa,
    operator_name: operatorName,
    operator_ropo: operatorRopo,
    delivery_note_number: deliveryNoteNumber,
  }
  for (const [key, value] of Object.entries(optional)) {
    if (value !== '' && value != null) form.append(key, value)
  }

  const response = await fetch(`/api/interventions/${interventionId}/execution`, {
    method: 'PATCH',
    headers: await authHeader(),
    body: form,
  })
  return unwrap(response)
}

// GET /api/interventions/:id — one record in full for the detail screen
// (richer than the list: justification, real applied data, raw transcription,
// plus plot/holding/equipment context). Scoped to the advisor server-side, so an
// unknown or foreign id comes back as a 404 whose `mensaje` we surface.
export async function getIntervention(interventionId) {
  const response = await fetch(`/api/interventions/${interventionId}`, {
    headers: await authHeader(),
  })
  return unwrap(response)
}

// PATCH /api/interventions/:id/effectiveness — rate an executed treatment's
// effectiveness (EXECUTED -> ASSESSED, FLUJO C). `effectiveness` is GOOD|FAIR|POOR
// (the backend validates the enum); `effectivenessDate` is when the advisor
// judged the result (a plain YYYY-MM-DD, prefilled to the device date but
// editable — the assessment happens days after the treatment); `effectivenessNotes`
// is the optional reason, sent only when present. Form-encoded like the others.
export async function assessEffectiveness(
  interventionId,
  { effectiveness, effectivenessDate, effectivenessNotes },
) {
  const form = new FormData()
  form.append('effectiveness', effectiveness)
  form.append('effectiveness_date', effectivenessDate)
  if (effectivenessNotes && effectivenessNotes.trim() !== '') {
    form.append('effectiveness_notes', effectivenessNotes)
  }

  const response = await fetch(`/api/interventions/${interventionId}/effectiveness`, {
    method: 'PATCH',
    headers: await authHeader(),
    body: form,
  })
  return unwrap(response)
}

// DELETE /api/interventions/:id — soft-deletes a record (M8.2): the backend
// keeps the row (legal retention) but it stops being visible everywhere. A
// 204 has no body, so this returns nothing; a 404/422 throws with the Spanish
// `mensaje` like every other call.
export async function deleteIntervention(interventionId) {
  const response = await fetch(`/api/interventions/${interventionId}`, {
    method: 'DELETE',
    headers: await authHeader(),
  })
  if (response.status === 204) return
  await unwrap(response) // non-2xx: throws with the backend's mensaje
}

// POST /api/interventions/:id/correction — corrects a record by SUPERSEDING it
// (M8.2): the backend saves a NEW record with the edited fields (re-validated
// like a fresh one) and soft-deletes the old one. Leaner body than /api/records:
// no device_timestamp (the replacement keeps the ORIGINAL dictation's date — a
// correction fixes what the record says, not when it happened) and no
// transcription (the audit trail is inherited). `transactionId` is a FRESH
// crypto.randomUUID captured once and reused on retry (idempotency, rule 3).
// Returns the saved replacement record.
export async function correctIntervention(interventionId, { fields, transactionId }) {
  const response = await fetch(`/api/interventions/${interventionId}/correction`, {
    method: 'POST',
    headers: { ...(await authHeader()), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fields, transaction_id: transactionId }),
  })
  return unwrap(response)
}

// POST /api/transcribe — speech-to-text ONLY (no extraction, no persistence).
// Used to dictate the assessment reason: returns the transcribed text so the PWA
// can drop it into an editable box for the advisor to review before submitting.
export async function transcribeAudio(audioBlob) {
  const form = new FormData()
  form.append('audio', audioBlob, 'note.webm')

  const response = await fetch('/api/transcribe', {
    method: 'POST',
    headers: await authHeader(),
    body: form,
  })
  const { text } = await unwrap(response)
  return text
}

// GET /api/interventions/:id/pdf — signs the prescription PDF link on demand
// (the list carries only has_pdf, never a per-row URL). Returns the presigned
// URL, valid for a short while; the caller opens it.
export async function getPdfUrl(interventionId) {
  const response = await fetch(`/api/interventions/${interventionId}/pdf`, {
    headers: await authHeader(),
  })
  const { pdf_url } = await unwrap(response)
  return pdf_url
}

// GET /api/holdings — the advisor's holdings, each with its plots and all its
// validations (M7). The validation screen groups them by holding (a validation
// is the HOLDING's, not a plot's) and, within each, by campaign.
export async function listHoldings() {
  const response = await fetch('/api/holdings', {
    headers: await authHeader(),
  })
  return unwrap(response)
}

// POST /api/holdings/:id/validations — signs a campaign validation (MID_CYCLE or
// FINAL). `validationDate` is the device clock (the advisor may sign offline);
// the backend derives the covered period and counts the interventions in it. A
// non-conform validation must carry `remarks` (the backend enforces it). The
// response includes a presigned link to the just-generated PDF. Form-encoded
// like the other write endpoints.
export async function createValidation(
  holdingId,
  { campaign, validationType, conformity, validationDate, remarks },
) {
  const form = new FormData()
  form.append('campaign', campaign)
  form.append('validation_type', validationType)
  form.append('conformity', conformity ? 'true' : 'false')
  form.append('validation_date', validationDate)
  if (remarks && remarks.trim() !== '') form.append('remarks', remarks)

  const response = await fetch(`/api/holdings/${holdingId}/validations`, {
    method: 'POST',
    headers: await authHeader(),
    body: form,
  })
  return unwrap(response)
}

// GET /api/validations/:id/pdf — signs the signed-validation PDF link on demand
// (the list carries only has_pdf). Returns the presigned URL; the caller opens it.
export async function getValidationPdfUrl(validationId) {
  const response = await fetch(`/api/validations/${validationId}/pdf`, {
    headers: await authHeader(),
  })
  const { pdf_url } = await unwrap(response)
  return pdf_url
}
