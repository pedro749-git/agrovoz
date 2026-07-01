import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from './supabase.js'
import Recorder from './Recorder.jsx'
import TodayList from './TodayList.jsx'

// The main screen: record button on top, today's records below. Unchanged from
// before the router — only "Ajustes" now navigates to its route instead of
// toggling a useState flag.
function Home() {
  const navigate = useNavigate()
  // Bumped after each saved recording to make TodayList re-fetch.
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <header className="bg-olive-d px-4 pb-3 pt-safe text-white">
        <div className="flex items-center justify-between pt-3">
          <div>
            <div className="text-sm font-semibold tracking-wide">AgroVoz</div>
            <div className="text-[10px] opacity-70">Cuaderno de campo por voz</div>
          </div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => navigate('/ajustes')}
              className="text-xs font-semibold opacity-80 underline"
            >
              Ajustes
            </button>
            <button
              type="button"
              onClick={() => supabase.auth.signOut()}
              className="text-xs font-semibold opacity-80 underline"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-6 pb-safe">
        <section className="flex flex-col items-center pt-10">
          <Recorder onSaved={() => setRefreshKey((k) => k + 1)} />
        </section>

        <section className="mx-auto mt-10 w-full max-w-md pb-8">
          <h2 className="text-sm font-bold uppercase tracking-wider text-ink">Hoy</h2>
          <TodayList refreshKey={refreshKey} />
        </section>
      </main>
    </div>
  )
}

export default Home
