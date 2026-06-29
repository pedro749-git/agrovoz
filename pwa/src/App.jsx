import { useState } from 'react'
import { useSession } from './useSession.js'
import { supabase } from './supabase.js'
import Login from './Login.jsx'
import Settings from './Settings.jsx'
import Recorder from './Recorder.jsx'
import TodayList from './TodayList.jsx'

function App() {
  const { session, loading } = useSession()
  // Bumped after each saved recording to make TodayList re-fetch.
  const [refreshKey, setRefreshKey] = useState(0)
  // Toggles the settings screen (where the advisor can set a password).
  const [showSettings, setShowSettings] = useState(false)

  // While we read the persisted session, show nothing — avoids flashing the
  // login screen for a user who is in fact already authenticated.
  if (loading) {
    return <div className="min-h-dvh bg-bone" />
  }

  // Not logged in -> the login screen (email OTP code / password). `useSession`
  // flips us to the app automatically once the session appears.
  if (!session) {
    return <Login />
  }

  // Settings is a full screen layered over the app; "Volver" closes it.
  if (showSettings) {
    return <Settings session={session} onClose={() => setShowSettings(false)} />
  }

  return (
    // Full-height screen: paper-like background, dark soil text.
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      {/* Top bar: dark olive, fills behind the notch. */}
      <header className="bg-olive-d px-4 pb-3 pt-safe text-white">
        <div className="flex items-center justify-between pt-3">
          <div>
            <div className="text-sm font-semibold tracking-wide">AgroVoz</div>
            <div className="text-[10px] opacity-70">Cuaderno de campo por voz</div>
          </div>
          <div className="flex items-center gap-4">
            {/* Settings: set/change password. */}
            <button
              type="button"
              onClick={() => setShowSettings(true)}
              className="text-xs font-semibold opacity-80 underline"
            >
              Ajustes
            </button>
            {/* Logout: ends the Supabase session; useSession sends us to Login. */}
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

      {/* Content: the record button on top, today's records below. Scrolls as
          the list grows; pb-safe keeps the last row off the gesture bar. */}
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

export default App
