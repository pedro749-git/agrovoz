import { useRef, useState } from 'react'
import { createRecord } from './api.js'
import Icon from './Icon.jsx'

// Records an audio note and uploads it to the backend, which transcribes,
// extracts the legal fields, validates and persists it. `onSaved` lets the
// parent refresh the day's list once a record lands.
//
// A component is just a function that returns the UI (JSX). React calls it to
// paint the screen, and re-calls it ("re-render") whenever its state changes.
function Recorder({ onSaved }) {
  // --- State: values that, when they change, repaint the screen ---
  const [isRecording, setIsRecording] = useState(false) // are we recording now?
  // The finished take, kept so the advisor can replay it AND so a failed upload
  // can be retried with the SAME idempotency key / device timestamp.
  const [take, setTake] = useState(null) // { url, blob, transactionId, deviceTimestamp }
  const [upload, setUpload] = useState('idle') // idle | sending | done | error
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
      setUpload('idle')
      setTake(null)
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

  // Send the take to the backend. Reuses take.transactionId, so pressing
  // "Enviar" again after a network error is a safe retry, not a duplicate.
  async function submit() {
    if (!take) return
    setUpload('sending')
    setError(null)
    try {
      await createRecord({
        audioBlob: take.blob,
        transactionId: take.transactionId,
        deviceTimestamp: take.deviceTimestamp,
      })
      setUpload('done')
      setTake(null) // clear the preview; the new record now appears in the list
      onSaved?.() // ask the parent to refresh today's list
    } catch (err) {
      // The backend's Spanish `mensaje` (a dose/area legal error, a missing
      // field, ...) IS the feedback — show it verbatim.
      setError(err.message)
      setUpload('error')
    }
  }

  return (
    <div className="flex flex-col items-center">
      {/* Big round record button: olive when idle, terracotta + pulsing while
          recording. One button toggles both. Disabled during an upload. A soft
          expanding ring behind it gives the recording state a live "listening"
          feel; the mic glyph replaces the old emoji. */}
      <div className="relative flex h-44 w-44 items-center justify-center">
        {isRecording && (
          <span className="absolute inset-0 animate-ping rounded-full bg-terra/25" />
        )}
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={upload === 'sending'}
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
      {upload === 'done' && (
        <p className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-moss">
          <Icon name="check-circle" className="h-4 w-4" />
          Registro guardado.
        </p>
      )}

      {/* Any error: mic access, or the backend's Spanish message. */}
      {error && (
        <p className="mt-4 flex max-w-[17rem] items-start gap-1.5 text-center text-sm text-terra">
          <Icon name="alert-triangle" className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="text-left">{error}</span>
        </p>
      )}

      {/* Review + send: appears once there is a finished take. */}
      {take && (
        <div className="mt-8 w-full max-w-xs rounded-2xl border border-line bg-card p-4 shadow-card">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-ink">
            Tu grabación
          </p>
          <audio controls src={take.url} className="w-full" />
          <button
            type="button"
            onClick={submit}
            disabled={upload === 'sending'}
            className="mt-4 w-full rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
          >
            {upload === 'sending'
              ? 'Procesando…'
              : upload === 'error'
                ? 'Reintentar envío'
                : 'Enviar registro'}
          </button>
        </div>
      )}
    </div>
  )
}

export default Recorder
