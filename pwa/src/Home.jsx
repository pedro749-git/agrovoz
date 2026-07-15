import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from './supabase.js'
import { deletePending, listPending } from './pendingTakes.js'
import AppBar, { BarButton } from './AppBar.jsx'
import Icon from './Icon.jsx'
import PendingList from './PendingList.jsx'
import Recorder from './Recorder.jsx'
import TodayList from './TodayList.jsx'

// The main screen: record button on top, offline-pending recordings (if any),
// then today's records. The header actions are icon buttons in the shared
// AppBar; "Ajustes" navigates to its route instead of toggling a useState flag.
function Home() {
  const navigate = useNavigate()
  // Bumped after each saved recording to make TodayList re-fetch.
  const [refreshKey, setRefreshKey] = useState(0)

  // Recordings queued while offline (IndexedDB, see pendingTakes.js). Read once
  // on mount and re-read whenever the Recorder queues/clears one or a card is
  // discarded here.
  const [pendingTakes, setPendingTakes] = useState([])
  // Handle the Recorder publishes its restoreTake() on (useImperativeHandle):
  // retrying a queued take is an event, so Home calls it instead of passing the
  // take down as a prop.
  const recorderRef = useRef(null)
  // The <main> element is the scroll container (overflow-y-auto), so scrolling
  // back to the record button must target it, not the window.
  const mainRef = useRef(null)

  const refreshPending = useCallback(() => {
    listPending().then(setPendingTakes).catch(console.error)
  }, [])

  useEffect(() => {
    refreshPending()
  }, [refreshPending])

  function retryPending(take) {
    recorderRef.current?.restoreTake(take)
    mainRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function discardPending(take) {
    // Destructive for the audio (though never a legal record — it was never
    // persisted), so ask first, like the record delete does.
    if (!window.confirm('¿Descartar esta grabación pendiente? El audio se perderá.')) {
      return
    }
    try {
      await deletePending(take.transactionId)
    } catch (err) {
      console.error(err)
    }
    refreshPending()
  }

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <AppBar
        title="Agrovoz"
        subtitle="Cuaderno de campo por voz"
        actions={
          <>
            <BarButton
              icon="shield-check"
              title="Validaciones"
              onClick={() => navigate('/validaciones')}
            />
            <BarButton icon="settings" title="Ajustes" onClick={() => navigate('/ajustes')} />
            <BarButton icon="log-out" title="Salir" onClick={() => supabase.auth.signOut()} />
          </>
        }
      />

      <main ref={mainRef} className="flex-1 overflow-y-auto px-6 pb-safe">
        <section className="flex flex-col items-center pt-10">
          <Recorder
            onSaved={() => setRefreshKey((k) => k + 1)}
            restoreRef={recorderRef}
            onPendingChange={refreshPending}
          />
        </section>

        <PendingList takes={pendingTakes} onRetry={retryPending} onDiscard={discardPending} />

        <section className="mx-auto mt-10 w-full max-w-md pb-8">
          <div className="mb-1 flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-ink">Hoy</h2>
            <button
              type="button"
              onClick={() => navigate('/historial')}
              className="inline-flex items-center gap-1 text-xs font-semibold text-olive transition active:scale-[0.97]"
            >
              <Icon name="calendar" className="h-4 w-4" />
              Historial
            </button>
          </div>
          <TodayList refreshKey={refreshKey} />
        </section>
      </main>
    </div>
  )
}

export default Home
