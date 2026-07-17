import { useImperativeHandle, useRef, useState } from 'react'
import { commitRecord, previewRecord } from './api.js'
import { deletePending, savePending } from './pendingTakes.js'
import Icon from './Icon.jsx'
import ReviewForm from './ReviewForm.jsx'

// What the backend is (roughly) doing during the preview call, in order.
const PREVIEW_STAGES = [
  'Transcribiendo audio…',
  'Extrayendo campos…',
  'Comprobando catálogo…',
]

// Records an audio note and drives the two-phase FLUJO A (M8): the audio is first
// PREVIEWED (transcribe + extract, nothing saved), the advisor reviews/corrects
// the extracted fields in ReviewForm, and only then are they COMMITTED to the
// legal record (hard rule 4: nothing from the LLM reaches the record unseen).
// `onSaved` lets the parent refresh the day's list once a record lands.
//
// Offline: when the preview/commit cannot reach the server at all, the take is
// parked in IndexedDB (see pendingTakes.js) instead of erroring. Home retries a
// queued take by calling `restoreTake` through `restoreRef` (see below), and
// `onPendingChange` tells Home to re-read the list after we queue or clear one.
//
// A component is just a function that returns the UI (JSX). React calls it to
// paint the screen, and re-calls it ("re-render") whenever its state changes.
function Recorder({ onSaved, restoreRef, onPendingChange }) {
  // --- State: values that, when they change, repaint the screen ---
  const [isRecording, setIsRecording] = useState(false) // are we recording now?
  // The finished take, kept so the advisor can replay it AND so a retry reuses
  // the SAME idempotency key / device timestamp.
  const [take, setTake] = useState(null) // { url, blob, transactionId, deviceTimestamp }
  // The preview result once the audio is transcribed + extracted; drives the
  // review form. null until phase 1 succeeds.
  const [preview, setPreview] = useState(null) // { transcription, fields }
  const [status, setStatus] = useState('idle') // idle | previewing | committing | queued | done
  const [error, setError] = useState(null) // Spanish message shown on failure
  // Machine code of the last COMMIT failure ("DOSE_ERROR", ...), so ReviewForm
  // can render legal-validation blocks as a highlighted card. Only meaningful
  // while `error` is set — it is overwritten together with it on every commit.
  const [errorCode, setErrorCode] = useState(null)
  // Index into PREVIEW_STAGES while previewing. The stages are TIMED, not real
  // progress: the preview is one backend call, so the PWA cannot know which
  // step (transcribe / extract / resolve) is running — this only makes the
  // multi-second wait legible instead of a frozen label.
  const [previewStage, setPreviewStage] = useState(0)

  // Loads a queued take as the current one, so it drives the normal preview →
  // review → commit flow with its ORIGINAL transactionId / deviceTimestamp
  // (hard rules 3 and 2 — the record keeps the clock of when it was dictated in
  // the field, not of the retry). `fromPending` marks it so a successful commit
  // also clears its queue entry.
  function restoreTake(pendingTake) {
    setTake((previous) => {
      if (previous) URL.revokeObjectURL(previous.url)
      return {
        url: URL.createObjectURL(pendingTake.blob),
        blob: pendingTake.blob,
        transactionId: pendingTake.transactionId,
        deviceTimestamp: pendingTake.deviceTimestamp,
        fromPending: true,
      }
    })
    setPreview(null)
    setStatus('idle')
    setError(null)
  }

  // Retrying is an EVENT (the advisor tapped "Reintentar"), not render data, so
  // instead of reacting to a prop in an effect, Home calls restoreTake directly:
  // useImperativeHandle publishes it on the ref Home passes in.
  useImperativeHandle(restoreRef, () => ({ restoreTake }))

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

  // No network: park the take in IndexedDB and clear the screen. The advisor
  // retries it by hand from Home's "Pendientes" list when coverage returns.
  async function queueTake() {
    try {
      await savePending(take)
      setTake((previous) => {
        if (previous) URL.revokeObjectURL(previous.url)
        return null
      })
      setPreview(null)
      setError(null)
      setStatus('queued')
      onPendingChange?.()
    } catch (err) {
      // IndexedDB refused the write (private mode, quota). The take is still on
      // screen, so ask the advisor to keep the app open instead of losing audio.
      setError(
        'Sin conexión, y no se pudo guardar el audio en el dispositivo. ' +
          'Mantén la app abierta y reintenta cuando tengas cobertura.',
      )
      setStatus('idle')
      console.error(err)
    }
  }

  // Phase 1: transcribe + extract the take, WITHOUT saving. Side-effect free, so
  // pressing it again after a failure is a plain retry. Unreachable server →
  // queue instead of erroring; a 422 with a Spanish mensaje still shows as error
  // (there IS connection — queueing it again would never fix it).
  async function runPreview() {
    if (!take) return
    if (!navigator.onLine) return queueTake()
    setStatus('previewing')
    setError(null)
    setPreviewStage(0)
    // Advance the label every 1.2s — quick enough that a ~3s preview still
    // shows all three stages — and hold at the last one until the call returns.
    // `finally` clears the timer on every exit path, including the early
    // `return queueTake()`.
    const stageTimer = setInterval(() => {
      setPreviewStage((stage) => Math.min(stage + 1, PREVIEW_STAGES.length - 1))
    }, 1200)
    try {
      setPreview(await previewRecord(take.blob))
      setStatus('idle')
    } catch (err) {
      if (err.isNetwork) return queueTake()
      setError(err.message)
      setStatus('idle')
    } finally {
      clearInterval(stageTimer)
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
      if (take.fromPending) {
        // Best-effort cleanup: if it fails, retrying the stale entry is harmless
        // — the reused transactionId makes the backend return the existing
        // record instead of duplicating it (hard rule 3).
        await deletePending(take.transactionId).catch(console.error)
        onPendingChange?.()
      }
      setStatus('done')
      setTake(null) // clear the preview; the new record now appears in the list
      setPreview(null)
      onSaved?.() // ask the parent to refresh today's list
    } catch (err) {
      // Connection dropped between review and confirm: queue the take so the
      // reviewed audio survives; the retry replays preview → review → commit.
      if (err.isNetwork) return queueTake()
      // The backend's Spanish `mensaje` (a dose/area legal error, a missing
      // field, ...) IS the feedback — show it in the form so the advisor fixes
      // the value and resubmits. The code tells ReviewForm HOW to show it.
      setError(err.message)
      setErrorCode(err.code ?? null)
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
          className={`relative flex h-40 w-40 flex-col items-center justify-center rounded-full text-white shadow-float ring-4 ring-white/70 transition hover:brightness-95 active:scale-95 disabled:opacity-60 ${
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

      {/* Hint only while recording: stopping is the non-obvious gesture (same
          button). Idle needs no caption — the button says REGISTRAR and the
          empty today-list already teaches what to dictate; a permanent line
          here just crowded the screen. */}
      {isRecording && (
        <p className="mt-6 max-w-[15rem] text-center text-sm leading-relaxed text-ink">
          Pulsa de nuevo para terminar la grabación.
        </p>
      )}

      {/* Saved confirmation (clears the preview). */}
      {status === 'done' && (
        <p className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-moss">
          <Icon name="check-circle" className="h-4 w-4" />
          Registro guardado.
        </p>
      )}

      {/* Offline: the take was parked in the pending queue, nothing was lost. */}
      {status === 'queued' && (
        <p className="mt-4 flex max-w-[17rem] items-start gap-1.5 text-sm font-semibold text-amber">
          <Icon name="cloud" className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="text-left">
            Sin conexión. El audio se ha guardado en «Pendientes de sincronizar»;
            reintenta cuando tengas cobertura.
          </span>
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
                ? PREVIEW_STAGES[previewStage]
                : error
                  ? 'Reintentar'
                  : 'Transcribir y revisar'}
            </button>
            <button
              type="button"
              onClick={discard}
              disabled={status === 'previewing'}
              className="text-xs font-semibold text-ink hover:underline"
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
          errorCode={errorCode}
        />
      )}
    </div>
  )
}

export default Recorder
