import { useState } from 'react'
import { supabase } from './supabase.js'
import AppBar from './AppBar.jsx'
import Icon from './Icon.jsx'

// Settings screen. For now its only job is letting an already-authenticated
// advisor set (or change) their password. Because the session is live, this is
// a single updateUser call — no recovery email needed. Once they have a
// password they can log in with the "Contraseña" tab instead of waiting for a
// code each time.
function Settings({ session, onClose }) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [status, setStatus] = useState('idle') // idle | saving | done | error
  const [error, setError] = useState(null)

  async function savePassword(event) {
    event.preventDefault()
    setError(null)

    if (password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres.')
      setStatus('error')
      return
    }
    if (password !== confirm) {
      setError('Las contraseñas no coinciden.')
      setStatus('error')
      return
    }

    setStatus('saving')
    const { error: authError } = await supabase.auth.updateUser({ password })

    if (authError) {
      setError('No se pudo guardar la contraseña. Inténtalo de nuevo.')
      setStatus('error')
      console.error(authError)
    } else {
      setStatus('done')
      setPassword('')
      setConfirm('')
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <AppBar title="Ajustes" subtitle={session.user.email} onBack={onClose} />

      <main className="flex-1 overflow-y-auto px-6 pb-safe">
        <section className="mx-auto mt-8 w-full max-w-xs">
          <h2 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.14em] text-ink">
            <Icon name="lock" className="h-4 w-4" />
            Contraseña
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-ink">
            Establece una contraseña para entrar sin esperar un código.
          </p>

          <form onSubmit={savePassword} className="mt-4">
            <input
              type="password"
              required
              autoComplete="new-password"
              placeholder="Nueva contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-line bg-card px-4 py-3 text-base outline-none focus:border-olive"
            />
            <input
              type="password"
              required
              autoComplete="new-password"
              placeholder="Repite la contraseña"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="mt-3 w-full rounded-xl border border-line bg-card px-4 py-3 text-base outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
            />

            {error && <p className="mt-3 text-sm text-terra">{error}</p>}
            {status === 'done' && (
              <p className="mt-3 text-sm font-semibold text-olive">
                Contraseña guardada.
              </p>
            )}

            <button
              type="submit"
              disabled={status === 'saving'}
              className="mt-4 w-full rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
            >
              {status === 'saving' ? 'Guardando…' : 'Guardar contraseña'}
            </button>
          </form>
        </section>
      </main>
    </div>
  )
}

export default Settings
