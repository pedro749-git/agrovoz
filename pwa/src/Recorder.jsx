import { useRef, useState } from 'react'
import { commitRecord, previewRecord } from './api.js'
import Icon from './Icon.jsx'
import ReviewForm from './ReviewForm.jsx'

// Records an audio note and drives the two-phase FLUJO A (M8): the audio is first
// PREVIEWED (transcribe + extract, nothing saved), the advisor reviews/corrects
// the extracted fields in ReviewForm, and only then are they COMMITTED to the
// legal record (hard rule 4: nothing from the LLM reaches the record unseen).
// `onSaved` lets the parent refresh the day's list once a record lands.
//
// A component is just a function that returns the UI (JSX). React calls it to
// paint the screen, and re-calls it ("re-render") whenever its state changes.
function Recorder({ onSaved }) {
  // --- State: values that, when they change, repaint the screen ---
  const [isRecording, setIsRecording] = useState(false) // are we recording now?
  // The finished take, kept so the advisor can replay it AND so a retry reuses
  // the SAME idempotency key / device timestamp.
  const [take, setTake] = useState(null) // { url, blob, transactionId, deviceTimestamp }
  // The preview result once the audio is transcribed + extracted; drives the
  // review form. null until phase 1 succeeds.
  const [preview, setPreview] = useState(null) // { transcription, fields }
  const [status, setStatus] = useState('idle') // idle | previewing | committing | done
  const [error, setError] = useState(null) // Spanish message shown on failure

  // --- Refs: mutable boxes that survive re-renders but DON'T repaint ---
  // The MediaRecorder and the audio pieces are "machinery", not UI.
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording() {
    setError(null)
    try {
      // Ask the browser/OS for the microphone (the "Allow microphone?" prompt).
      // Requires HTTPS — hence the cloudflared tunnel in dev.
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      // While recording, the recorder hands us the audio in pieces ("chunks").
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }

      // On stop, glue the chunks into one file (Blob) and capture, ONCE, the two
      // values a retry must reuse (hard rules 2 and 3):
      //   - deviceTimestamp: the device clock at the moment of recording.
      //   - transactionId: a client-generated idempotency key.
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        setTake((previous) => {
          if (previous) URL.revokeObjectURL(previous.url) // free the old preview
          return {
            url: URL.createObjectURL(blob),
            blob,
            transactionId: crypto.randomUUID(),
            deviceTimestamp: new Date().toISOString(),
          }
        })
        // Release the mic so the OS "recording" indicator turns off.
        stream.getTracks().forEach((track) => track.stop())
      }

      recorder.start()
      // Fresh take: clear any previous preview/status so the UI starts clean.
      setPreview(null)
      setTake(null)
      setStatus('idle')
      setIsRecording(true)
    } catch (err) {
      // Map the technical error to a readable Spanish message; full detail in
      // the console for debugging.
      const messages = {
        NotAllowedError:
          'Permiso de micrófono denegado. Actívalo en los ajustes del navegador.',
        NotFoundError: 'No se encontró ningún micrófono en el dispositivo.',
        NotReadableError: 'El micrófono está siendo usado por otra aplicación.',
      }
      setError(messages[err.name] ?? 'No se pudo acceder al micrófono.')
      console.error(err)
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop() // triggers the onstop handler above
    setIsRecording(false)
  }

  // Phase 1: transcribe + extract the take, WITHOUT saving. Side-effect free, so
  // pressing it again after a failure is a plain retry.
  async function runPreview() {
    if (!take) return
    setStatus('previewing')
    setError(null)
    try {
      setPreview(await previewRecord(take.blob))
      setStatus('idle')
    } catch (err) {
      setError(err.message)
      setStatus('idle')
    }
  }

  // Phase 2: persist the advisor-reviewed fields. Reuses take.transactionId, so
  // a network-error retry hits the existing row instead of duplicating a record.
  // The original transcription is sent as the audit trail.
  async function runCommit(fields) {
    setStatus('committing')
    setError(null)
    try {
      await commitRecord({
        fields,
        transactionId: take.transactionId,
        deviceTimestamp: take.deviceTimestamp,
        transcription: preview.transcription,
      })
      setStatus('done')
      setTake(null) // clear the preview; the new record now appears in the list
      setPreview(null)
      onSaved?.() // ask the parent to refresh today's list
    } catch (err) {
      // The backend's Spanish `mensaje` (a dose/area legal error, a missing
      // field, ...) IS the feedback — show it in the form so the advisor fixes
      // the value and resubmits.
      setError(err.message)
      setStatus('idle')
    }
  }

  // Discard the take + preview and go back to the record button.
  function discard() {
    setTake((previous) => {
      if (previous) URL.revokeObjectURL(previous.url)
      return null
    })
    setPreview(null)
    setStatus('idle')
    setError(null)
  }

  return (
    <div className="flex flex-col items-center">
      {/* Big round record button: olive when idle, terracotta + pulsing while
          recording. One button toggles both. Disabled during a preview/commit. */}
      <div className="relative flex h-44 w-44 items-center justify-center">
        {isRecording && (
          <span className="absolute inset-0 animate-ping rounded-full bg-terra/25" />
        )}
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={status === 'previewing' || status === 'committing'}
          className={`relative flex h-40 w-40 flex-col items-center justify-center rounded-full text-white shadow-float ring-4 ring-white/70 transition active:scale-95 disabled:opacity-60 ${
            isRecording ? 'bg-terra' : 'bg-gradient-to-b from-olive to-olive-d'
          }`}
        >
          <Icon
            name={isRecording ? 'stop' : 'mic'}
            className="h-9 w-9"
            strokeWidth={isRecording ? 0 : 2}
          />
          <span className="mt-1.5 text-xs font-bold tracking-[0.18em]">
            {isRecording ? 'GRABANDO' : 'REGISTRAR'}
          </span>
        </button>
      </div>

      {/* Hint text under the button. */}
      <p className="mt-6 max-w-[15rem] text-center text-sm leading-relaxed text-ink">
        {isRecording
          ? 'Pulsa de nuevo para terminar la grabación.'
          : 'Dicta una observación o una prescripción. El sistema reconoce cuál es.'}
      </p>

      {/* Saved confirmation (clears the preview). */}
      {status === 'done' && (
        <p className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-moss">
          <Icon name="check-circle" className="h-4 w-4" />
          Registro guardado.
        </p>
      )}

      {/* A mic-access or preview error shown before the review form exists. */}
      {error && !preview && (
        <p className="mt-4 flex max-w-[17rem] items-start gap-1.5 text-center text-sm text-terra">
          <Icon name="alert-triangle" className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="text-left">{error}</span>
        </p>
      )}

      {/* Review the audio + send it to preview: appears once there is a take and
          before it has been previewed. */}
      {take && !preview && (
        <div className="mt-8 w-full max-w-xs rounded-2xl border border-line bg-card p-4 shadow-card">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-ink">
            Tu grabación
          </p>
          <audio controls src={take.url} className="w-full" />
          <div className="mt-4 flex items-center gap-4">
            <button
              type="button"
              onClick={runPreview}
              disabled={status === 'previewing'}
              className="flex-1 rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
            >
              {status === 'previewing'
                ? 'Transcribiendo…'
                : error
                  ? 'Reintentar'
                  : 'Transcribir y revisar'}
            </button>
            <button
              type="button"
              onClick={discard}
              disabled={status === 'previewing'}
              className="text-xs font-semibold text-ink"
            >
              Descartar
            </button>
          </div>
        </div>
      )}

      {/* Phase 2: the editable review of the extracted fields. */}
      {preview && (
        <ReviewForm
          transcription={preview.transcription}
          fields={preview.fields}
          resolution={preview.resolution}
          onConfirm={runCommit}
          onCancel={discard}
          submitting={status === 'committing'}
          error={error}
        />
      )}
    </div>
  )
}

export default Recorder
