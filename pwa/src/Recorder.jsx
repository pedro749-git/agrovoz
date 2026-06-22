import { useRef, useState } from 'react'

// A component is just a function that returns the UI (JSX). React calls it to
// paint the screen, and re-calls it ("re-render") whenever its state changes.
function Recorder() {
  // --- State: values that, when they change, make React repaint the screen ---
  const [isRecording, setIsRecording] = useState(false) // are we recording now?
  const [audioUrl, setAudioUrl] = useState(null) // playable URL of the last take
  const [error, setError] = useState(null) // Spanish message shown if it fails

  // --- Refs: mutable boxes that survive re-renders but DON'T repaint ---
  // The MediaRecorder and the audio pieces are "machinery", not UI, so they
  // live in refs: we mutate them without triggering a re-render.
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording() {
    setError(null)
    try {
      // Ask the browser/OS for the microphone. Returns a Promise, so we await.
      // This shows the "Allow microphone?" prompt. Requires HTTPS (the tunnel).
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // The object that records the audio stream into memory.
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      // While recording, the recorder hands us the audio in pieces ("chunks").
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }

      // On stop, glue the chunks into one file (Blob) and make a URL the
      // <audio> player can read.
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        const url = URL.createObjectURL(blob)
        setAudioUrl((previousUrl) => {
          if (previousUrl) URL.revokeObjectURL(previousUrl) // free the old one
          return url
        })
        // Release the mic so the OS "recording" indicator turns off.
        stream.getTracks().forEach((track) => track.stop())
      }

      recorder.start()
      setIsRecording(true)
    } catch (err) {
      // Map the technical error name to a readable Spanish message; the full
      // detail stays in the console for debugging.
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

  return (
    <div className="flex flex-col items-center">
      {/* Big round record button (prototype `.rec-btn`): olive when idle,
          terracotta + pulsing while recording. One button toggles both. */}
      <button
        type="button"
        onClick={isRecording ? stopRecording : startRecording}
        className={`flex h-40 w-40 flex-col items-center justify-center rounded-full border-4 border-white text-white shadow-xl transition active:scale-95 ${
          isRecording ? 'animate-pulse bg-terra' : 'bg-olive'
        }`}
      >
        <span className="text-4xl">🎙️</span>
        <span className="mt-1 text-sm font-bold tracking-widest">
          {isRecording ? 'GRABANDO' : 'REGISTRAR'}
        </span>
      </button>

      {/* Hint text under the button (prototype `.rec-hint`). */}
      <p className="mt-5 max-w-[15rem] text-center text-sm leading-relaxed text-ink">
        {isRecording
          ? 'Pulsa de nuevo para terminar la grabación.'
          : 'Dicta una observación o una prescripción. El sistema reconoce cuál es.'}
      </p>

      {/* Conditional rendering: shown only when `error` has a value. */}
      {error && <p className="mt-4 text-sm text-terra">{error}</p>}

      {/* Playback: appears only once there is a recording. */}
      {audioUrl && (
        <div className="mt-8 w-full max-w-xs">
          <p className="mb-2 text-xs font-bold uppercase tracking-wider text-ink">
            Tu grabación
          </p>
          <audio controls src={audioUrl} className="w-full" />
        </div>
      )}
    </div>
  )
}

export default Recorder
