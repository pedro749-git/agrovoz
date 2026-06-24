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

// GET /api/interventions — the advisor's records, newest first.
export async function listInterventions() {
  const response = await fetch('/api/interventions', {
    headers: await authHeader(),
  })
  return unwrap(response)
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
