import { useCallback, useEffect, useRef, useState } from 'react'
import { deletePending, listPending } from './pendingTakes.js'
import AppBar from './AppBar.jsx'
import BottomNav from './BottomNav.jsx'
import ConfirmDialog from './ConfirmDialog.jsx'
import PendingList from './PendingList.jsx'
import Recorder from './Recorder.jsx'
import TodayList from './TodayList.jsx'

// The main screen: record button on top, offline-pending recordings (if any),
// then today's records. Navigation lives in the shared BottomNav — the record
// button stays HERE, big and unmistakable; the bar's centre button only leads
// back to this screen.
function Home() {
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

  // Destructive for the audio (though never a legal record — it was never
  // persisted), so ask first via the in-app dialog: the take waits here until
  // the advisor confirms or cancels.
  const [takeToDiscard, setTakeToDiscard] = useState(null)

  async function discardPending() {
    const take = takeToDiscard
    setTakeToDiscard(null)
    try {
      await deletePending(take.transactionId)
    } catch (err) {
      console.error(err)
    }
    refreshPending()
  }

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <AppBar title="AgroVoz" subtitle="Cuaderno de campo por voz" />

      {/* pb-44 keeps the last card clear of the floating bottom bar. */}
      <main ref={mainRef} className="flex-1 overflow-y-auto px-6 pb-44">
        <section className="flex flex-col items-center pt-6">
          <Recorder
            onSaved={() => setRefreshKey((k) => k + 1)}
            restoreRef={recorderRef}
            onPendingChange={refreshPending}
          />
        </section>

        <PendingList takes={pendingTakes} onRetry={retryPending} onDiscard={setTakeToDiscard} />

        <section className="mx-auto mt-8 w-full max-w-md">
          <h2 className="mb-1 text-xs font-bold uppercase tracking-[0.14em] text-ink">Hoy</h2>
          <TodayList refreshKey={refreshKey} />
        </section>
      </main>

      <BottomNav />

      <ConfirmDialog
        open={takeToDiscard !== null}
        title="¿Descartar esta grabación?"
        body="El audio pendiente se perderá y no se podrá recuperar."
        confirmLabel="Descartar"
        onConfirm={discardPending}
        onCancel={() => setTakeToDiscard(null)}
      />
    </div>
  )
}

export default Home
