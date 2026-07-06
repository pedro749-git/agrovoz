import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from './supabase.js'
import AppBar, { BarButton } from './AppBar.jsx'
import Icon from './Icon.jsx'
import Recorder from './Recorder.jsx'
import TodayList from './TodayList.jsx'

// The main screen: record button on top, today's records below. The header
// actions are now icon buttons in the shared AppBar; "Ajustes" navigates to its
// route instead of toggling a useState flag.
function Home() {
  const navigate = useNavigate()
  // Bumped after each saved recording to make TodayList re-fetch.
  const [refreshKey, setRefreshKey] = useState(0)

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

      <main className="flex-1 overflow-y-auto px-6 pb-safe">
        <section className="flex flex-col items-center pt-10">
          <Recorder onSaved={() => setRefreshKey((k) => k + 1)} />
        </section>

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
