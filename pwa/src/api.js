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
async function unwrap(response) {
  if (response.ok) return response.json()
  let mensaje = 'Error inesperado. Inténtalo de nuevo.'
  try {
    const body = await response.json()
    if (body?.mensaje) mensaje = body.mensaje
  } catch {
    // Non-JSON error body (e.g. a proxy 502): keep the generic message.
  }
  throw new Error(mensaje)
}

// POST /api/records — uploads one audio note. The backend transcribes,
// extracts, validates and persists, returning the saved record (or a 4xx whose
// `mensaje` we surface, e.g. a dose/area legal error).
//
// `transactionId` and `deviceTimestamp` are captured by the caller when the
// recording STOPS, not here, so a retry of the same take reuses both:
//   - transactionId (crypto.randomUUID) is the idempotency key (hard rule 3):
//     a flaky-network retry hits the existing row instead of duplicating a
//     legal record.
//   - deviceTimestamp is the device clock (hard rule 2): the treatment date is
//     when the advisor spoke in the field, never when the server received it.
export async function createRecord({ audioBlob, transactionId, deviceTimestamp }) {
  const form = new FormData()
  form.append('transaction_id', transactionId)
  form.append('device_timestamp', deviceTimestamp)
  // A filename lets the backend infer the audio type (MediaRecorder gives webm).
  form.append('audio', audioBlob, 'note.webm')

  const response = await fetch('/api/records', {
    method: 'POST',
    // NOTE: do not set Content-Type — the browser sets it WITH the multipart
    // boundary. Setting it by hand would corrupt the upload.
    headers: await authHeader(),
    body: form,
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
// the backend endpoint (Form(...)), exactly like createRecord.
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
