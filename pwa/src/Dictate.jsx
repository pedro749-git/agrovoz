import { useRef, useState } from 'react'
import { transcribeAudio } from './api.js'
import Icon from './Icon.jsx'

// A self-contained "dictate" button. Records a short note, sends it to
// POST /api/transcribe, and hands the text back through `onTranscribed` so the
// parent can drop it into an editable field (the advisor reviews what Qwen heard
// before saving). Reused by the effectiveness assessment and the campaign
// validation remarks — same mechanism, so it lives here once.
//
// Mirrors Recorder's mic handling: getUserMedia needs HTTPS (the cloudflared
// tunnel in dev), we collect chunks and, on stop, glue them into one blob and
// transcribe. The button owns its own little state machine; on error it invites
// a retry in place rather than surfacing a separate message.
function Dictate({ onTranscribed, label = 'Dictar', className = '' }) {
  const [state, setState] = useState('idle') // idle | recording | transcribing | error
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop()) // release the mic
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        setState('transcribing')
        try {
          onTranscribed(await transcribeAudio(blob))
          setState('idle')
        } catch (err) {
          console.error(err)
          setState('error')
        }
      }
      recorder.start()
      setState('recording')
    } catch (err) {
      console.error(err)
      setState('error')
    }
  }

  function stop() {
    mediaRecorderRef.current?.stop() // triggers onstop (transcription) above
  }

  const base =
    'inline-flex items-center gap-1.5 self-start rounded-lg px-3 py-2 text-xs font-semibold transition active:scale-[0.97]'
  return (
    <button
      type="button"
      onClick={state === 'recording' ? stop : start}
      disabled={state === 'transcribing'}
      className={`${base} ${
        state === 'recording'
          ? 'animate-pulse bg-terra/10 text-terra'
          : 'bg-olive/10 text-olive hover:bg-olive/20 disabled:opacity-50'
      } ${className}`}
    >
      <Icon name={state === 'recording' ? 'stop' : 'mic'} className="h-4 w-4" />
      {state === 'recording'
        ? 'Detener y transcribir'
        : state === 'transcribing'
          ? 'Transcribiendo…'
          : state === 'error'
            ? 'Micrófono falló — reintentar'
            : label}
    </button>
  )
}

export default Dictate
