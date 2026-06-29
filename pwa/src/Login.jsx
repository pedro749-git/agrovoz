import { useState } from 'react'
import { supabase } from './supabase.js'

// Login screen with two ways in:
//  - "code" (primary): the advisor types their email, we send a 6-digit code,
//    they type it back. We use a code instead of a magic link because tapping a
//    link from the mail app on iPhone can open a different browser than the one
//    holding the PWA, breaking the session — a code is copy-pasted (or typed)
//    into whichever browser already has the app open.
//  - "password" (secondary): email + password via signInWithPassword, for
//    advisors who set a password from inside the app (Ajustes). The "user" IS
//    the email — we do not have separate usernames.
// On success the app re-renders automatically because `useSession` is listening
// to auth changes.
function Login() {
  const [method, setMethod] = useState('code') // code | password
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [codeSent, setCodeSent] = useState(false) // code flow: email step -> code step
  const [status, setStatus] = useState('idle') // idle | sending | error
  const [error, setError] = useState(null)

  // Switching tab clears any in-flight state so the form is clean.
  function switchMethod(next) {
    setMethod(next)
    setStatus('idle')
    setError(null)
    setCodeSent(false)
    setCode('')
  }

  async function requestCode(event) {
    event.preventDefault() // keep the browser from reloading the page on submit
    setStatus('sending')
    setError(null)

    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        // Do not create an account: only advisors already registered in
        // Supabase may log in.
        shouldCreateUser: false,
      },
    })

    if (authError) {
      setError('No se pudo enviar el código. Revisa el correo e inténtalo de nuevo.')
      setStatus('error')
      console.error(authError)
    } else {
      setCodeSent(true) // move to the code-entry step
      setStatus('idle')
    }
  }

  async function verifyCode(event) {
    event.preventDefault()
    setStatus('sending')
    setError(null)

    const { error: authError } = await supabase.auth.verifyOtp({
      email,
      token: code.trim(),
      type: 'email',
    })

    if (authError) {
      setError('Código incorrecto o caducado. Pídelo de nuevo.')
      setStatus('error')
      console.error(authError)
    }
    // On success useSession picks up the new session and App swaps this screen.
  }

  async function signInWithPassword(event) {
    event.preventDefault()
    setStatus('sending')
    setError(null)

    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (authError) {
      // Supabase returns the same error for wrong password and unknown user, so
      // we keep the message generic on purpose (no account enumeration).
      setError('Correo o contraseña incorrectos.')
      setStatus('error')
      console.error(authError)
    }
    // On success useSession picks up the new session and App swaps this screen.
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
        <div className="w-full max-w-xs">
          <h1 className="text-center text-lg font-bold">Iniciar sesión</h1>

          {/* Tabs: pick how to sign in. */}
          <div className="mt-5 grid grid-cols-2 rounded-lg border border-line bg-card p-1 text-sm font-semibold">
            <button
              type="button"
              onClick={() => switchMethod('code')}
              className={`rounded-md py-2 transition ${
                method === 'code' ? 'bg-olive text-white shadow' : 'text-ink'
              }`}
            >
              Código
            </button>
            <button
              type="button"
              onClick={() => switchMethod('password')}
              className={`rounded-md py-2 transition ${
                method === 'password' ? 'bg-olive text-white shadow' : 'text-ink'
              }`}
            >
              Contraseña
            </button>
          </div>

          {method === 'code' && !codeSent && (
            <form onSubmit={requestCode} className="mt-5">
              <p className="text-center text-sm leading-relaxed text-ink">
                Introduce tu correo y te enviaremos un código de acceso.
              </p>

              <input
                type="email"
                required
                autoComplete="email"
                inputMode="email"
                placeholder="tu@correo.es"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-5 w-full rounded-lg border border-line bg-card px-4 py-3 text-base outline-none focus:border-olive"
              />

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-lg bg-olive py-3 font-bold text-white shadow transition active:scale-[0.98] disabled:opacity-60"
              >
                {status === 'sending' ? 'Enviando…' : 'Enviar código'}
              </button>
            </form>
          )}

          {method === 'code' && codeSent && (
            <form onSubmit={verifyCode} className="mt-5">
              <p className="text-center text-sm leading-relaxed text-ink">
                Hemos enviado un código a{' '}
                <span className="font-semibold text-soil">{email}</span>.
                Introdúcelo aquí.
              </p>

              <input
                type="text"
                required
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                className="mt-5 w-full rounded-lg border border-line bg-card px-4 py-3 text-center text-2xl tracking-[0.4em] outline-none focus:border-olive"
              />

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-lg bg-olive py-3 font-bold text-white shadow transition active:scale-[0.98] disabled:opacity-60"
              >
                {status === 'sending' ? 'Comprobando…' : 'Entrar'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setCodeSent(false)
                  setCode('')
                  setError(null)
                }}
                className="mt-4 w-full text-sm font-semibold text-olive underline"
              >
                Usar otro correo
              </button>
            </form>
          )}

          {method === 'password' && (
            <form onSubmit={signInWithPassword} className="mt-5">
              <p className="text-center text-sm leading-relaxed text-ink">
                Introduce tu correo y tu contraseña.
              </p>

              <input
                type="email"
                required
                autoComplete="email"
                inputMode="email"
                placeholder="tu@correo.es"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-5 w-full rounded-lg border border-line bg-card px-4 py-3 text-base outline-none focus:border-olive"
              />

              <input
                type="password"
                required
                autoComplete="current-password"
                placeholder="Contraseña"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-3 w-full rounded-lg border border-line bg-card px-4 py-3 text-base outline-none focus:border-olive"
              />

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-lg bg-olive py-3 font-bold text-white shadow transition active:scale-[0.98] disabled:opacity-60"
              >
                {status === 'sending' ? 'Entrando…' : 'Entrar'}
              </button>

              <p className="mt-4 text-center text-xs leading-relaxed text-ink">
                ¿No tienes contraseña? Entra con un código y créala en Ajustes.
              </p>
            </form>
          )}
        </div>
      </main>
    </div>
  )
}

export default Login
