import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useSession } from './useSession.js'
import { bootstrap } from './api.js'
import Login from './Login.jsx'
import Settings from './Settings.jsx'
import Home from './Home.jsx'
import Detail from './Detail.jsx'
import History from './History.jsx'
import Validation from './Validation.jsx'

// Wraps Settings (which takes an onClose) as a route element, sending "Volver"
// back home — Settings itself stays router-agnostic.
function SettingsRoute({ session }) {
  const navigate = useNavigate()
  return <Settings session={session} onClose={() => navigate('/')} />
}

function App() {
  const { session, loading } = useSession()
  const [booted, setBooted] = useState(false)

  // Hackathon self-signup only (TEMPORARY): a user who just registered has a
  // session but no advisor row yet. The signup flow set 'pending_bootstrap';
  // here we call /api/bootstrap ONCE to provision the demo advisor + sandbox
  // before Home mounts — Home's first list call would 401 without an advisor.
  // A normal login never sets the flag, so it skips this entirely (no extra
  // round trip). sessionStorage clears on tab close, so the flag never lingers.
  const needsBootstrap =
    !!session &&
    !booted &&
    sessionStorage.getItem('pending_bootstrap') === 'true'

  useEffect(() => {
    if (!needsBootstrap) return
    bootstrap()
      .catch((err) => console.error('bootstrap failed', err))
      .finally(() => {
        sessionStorage.removeItem('pending_bootstrap')
        setBooted(true) // proceed to the app whether or not it succeeded
      })
  }, [needsBootstrap])

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

  // Just signed up: hold on a brief "preparing your account" screen while the
  // sandbox is provisioned, so Home never mounts against a missing advisor.
  if (needsBootstrap) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-bone text-soil">
        <p className="text-sm font-semibold">Preparando tu cuenta…</p>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/historial" element={<History />} />
      <Route path="/registro/:id" element={<Detail />} />
      <Route path="/validaciones" element={<Validation />} />
      <Route path="/ajustes" element={<SettingsRoute session={session} />} />
      {/* Unknown path -> home (e.g. a stale deep link). */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
