import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useSession } from './useSession.js'
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
