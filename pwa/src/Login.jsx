import { useState } from 'react'
import { supabase } from './supabase.js'

// Magic-link login: the advisor types their email, we send a one-time link, and
// when they tap it Supabase brings them back already authenticated (no password
// to type or store — right for field users on phones). On success the app
// re-renders automatically because `useSession` is listening to auth changes.
function Login() {
  const [email, setEmail] = useState('')
  // Simple status machine driving what the screen shows.
  const [status, setStatus] = useState('idle') // idle | sending | sent | error
  const [error, setError] = useState(null)

  async function sendLink(event) {
    event.preventDefault() // keep the browser from reloading the page on submit
    setStatus('sending')
    setError(null)

    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        // The link returns to this same app (its current origin).
        emailRedirectTo: window.location.origin,
      },
    })

    if (authError) {
      setError('No se pudo enviar el enlace. Revisa el correo e inténtalo de nuevo.')
      setStatus('error')
      console.error(authError)
    } else {
      setStatus('sent') // the email is on its way; tell the advisor to check it
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <header className="bg-olive-d px-4 pb-3 pt-safe text-white">
        <div className="pt-3">
          <div className="text-sm font-semibold tracking-wide">AgroVoz</div>
          <div className="text-[10px] opacity-70">Cuaderno de campo por voz</div>
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-6 pb-safe">
        {status === 'sent' ? (
          // Confirmation: the link was sent. We stay here until they click it.
          <div className="max-w-xs text-center">
            <div className="text-5xl">📬</div>
            <h1 className="mt-4 text-lg font-bold">Revisa tu correo</h1>
            <p className="mt-2 text-sm leading-relaxed text-ink">
              Te hemos enviado un enlace de acceso a{' '}
              <span className="font-semibold text-soil">{email}</span>. Ábrelo en
              este dispositivo para entrar.
            </p>
            <button
              type="button"
              onClick={() => setStatus('idle')}
              className="mt-6 text-sm font-semibold text-olive underline"
            >
              Usar otro correo
            </button>
          </div>
        ) : (
          <form onSubmit={sendLink} className="w-full max-w-xs">
            <h1 className="text-center text-lg font-bold">Iniciar sesión</h1>
            <p className="mt-2 text-center text-sm leading-relaxed text-ink">
              Introduce tu correo y te enviaremos un enlace de acceso.
            </p>

            <input
              type="email"
              required
              autoComplete="email"
              inputMode="email"
              placeholder="tu@correo.es"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-6 w-full rounded-lg border border-line bg-card px-4 py-3 text-base outline-none focus:border-olive"
            />

            {error && <p className="mt-3 text-sm text-terra">{error}</p>}

            <button
              type="submit"
              disabled={status === 'sending'}
              className="mt-4 w-full rounded-lg bg-olive py-3 font-bold text-white shadow transition active:scale-[0.98] disabled:opacity-60"
            >
              {status === 'sending' ? 'Enviando…' : 'Enviar enlace'}
            </button>
          </form>
        )}
      </main>
    </div>
  )
}

export default Login
