import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { supabase } from './supabase.js'

// Hackathon self-signup (TEMPORARY — see docs/decisions.md). Only when the build
// sets VITE_HACKATHON_SIGNUP=true does the login expose a "Crear cuenta" path;
// otherwise the screen is login-only, the permanent design (admin alta). Read at
// build time (Vite inlines import.meta.env), so flipping it needs a rebuild.
const SIGNUP_ENABLED = import.meta.env.VITE_HACKATHON_SIGNUP === 'true'

// Cloudflare Turnstile site key, injected at build time. Empty (the default)
// means "captcha off": we send no token and Supabase must have captcha disabled.
// To turn it on for the hackathon: enable Turnstile in Supabase Auth, set
// VITE_TURNSTILE_SITE_KEY, and mount the widget where getCaptchaToken() reads it
// (see the stub below). Kept out of the login flow until then so nothing breaks.
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || ''

// Loads Cloudflare Turnstile's script once, in explicit-render mode, and resolves
// when window.turnstile is ready. Fetched lazily from the login screen (only when
// a site key is set), so a normal app visit never contacts Cloudflare. Captcha is
// OFF by default (empty key): then this never runs and no token is sent, which is
// what Supabase expects when its own captcha is disabled.
let turnstilePromise = null
function loadTurnstile() {
  if (window.turnstile) return Promise.resolve()
  if (turnstilePromise) return turnstilePromise
  turnstilePromise = new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    s.async = true
    s.defer = true
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
  return turnstilePromise
}

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

  // ── Cloudflare Turnstile captcha (only when a site key is configured) ──
  // Supabase's captcha protection is project-wide, so once it is enabled EVERY
  // credential endpoint here (send code, password, signup) must carry a token —
  // hence the widget lives on the whole login screen, not just signup. Until a
  // key is set, ACTIVE is false and nothing changes.
  const CAPTCHA_ACTIVE = Boolean(TURNSTILE_SITE_KEY)
  const [captchaToken, setCaptchaToken] = useState(null)
  const captchaRef = useRef(null) // the <div> the widget renders into
  const widgetIdRef = useRef(null) // Turnstile's handle, for reset()

  useEffect(() => {
    if (!CAPTCHA_ACTIVE) return
    let cancelled = false
    loadTurnstile()
      .then(() => {
        if (cancelled || !captchaRef.current || widgetIdRef.current !== null) return
        widgetIdRef.current = window.turnstile.render(captchaRef.current, {
          sitekey: TURNSTILE_SITE_KEY,
          // Token is single-use and expires; keep state in sync with the widget.
          callback: (token) => setCaptchaToken(token),
          'expired-callback': () => setCaptchaToken(null),
          'error-callback': () => setCaptchaToken(null),
        })
      })
      .catch(() => setError('No se pudo cargar la verificación de seguridad.'))
    return () => {
      cancelled = true
    }
  }, [CAPTCHA_ACTIVE])

  // A Turnstile token is burned once Supabase validates it, so after each
  // credential call we reset the widget to fetch a fresh one for any retry.
  function resetCaptcha() {
    if (!CAPTCHA_ACTIVE || widgetIdRef.current === null) return
    window.turnstile?.reset(widgetIdRef.current)
    setCaptchaToken(null)
  }

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

    // With captcha on, don't even call Supabase until the widget hands us a token.
    if (CAPTCHA_ACTIVE && !captchaToken) {
      setError('Completa la verificación de seguridad.')
      return
    }

    setStatus('sending')
    setError(null)

    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        // Normally we do NOT create accounts: only advisors already registered
        // in Supabase may log in (permanent design). The hackathon "Crear cuenta"
        // path is the sole exception — there we let the OTP create the user, and
        // /api/bootstrap turns it into a demo advisor after verification.
        shouldCreateUser: method === 'signup',
        // undefined when captcha is off; Supabase then ignores it.
        captchaToken: captchaToken || undefined,
      },
    })
    resetCaptcha() // token is single-use — get a fresh one for any retry

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

    // Signup only: mark that the app must provision this user (create the demo
    // advisor + sandbox) BEFORE loading Home, which would otherwise 401 with no
    // advisor row. Set before verifyOtp resolves so App sees it the instant the
    // session appears; cleared again if verification fails.
    if (method === 'signup') {
      sessionStorage.setItem('pending_bootstrap', 'true')
    }

    const { error: authError } = await supabase.auth.verifyOtp({
      email,
      token: code.trim(),
      type: 'email',
    })

    if (authError) {
      if (method === 'signup') sessionStorage.removeItem('pending_bootstrap')
      setError('Código incorrecto o caducado. Pídelo de nuevo.')
      setStatus('error')
      console.error(authError)
    }
    // On success useSession picks up the new session and App swaps this screen
    // (App runs the bootstrap first when the pending_bootstrap flag is set).
  }

  async function signInWithPassword(event) {
    event.preventDefault()

    if (CAPTCHA_ACTIVE && !captchaToken) {
      setError('Completa la verificación de seguridad.')
      return
    }

    setStatus('sending')
    setError(null)

    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
      options: { captchaToken: captchaToken || undefined },
    })
    resetCaptcha()

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
      {/* No AppBar here: the login is the app's cover page, and the brand
          appears once, big, instead of twice. pt-safe moves to <main>. */}
      <main className="flex flex-1 flex-col items-center justify-center px-6 pb-safe pt-safe">
        <div className="w-full max-w-xs">
          {/* Brand block. The product's identity is the voice, so the artistic
              mark is a spoken-word waveform over the wordmark: uneven bar
              heights (like real speech, not a symmetric equalizer) fading out
              at the edges, in the same olive ramp the buttons use. */}
          <div className="mb-9 text-center">
            <div className="flex items-end justify-center gap-1.5" aria-hidden="true">
              {[
                { h: 10, cls: 'bg-olive/30' },
                { h: 24, cls: 'bg-olive/60' },
                { h: 16, cls: 'bg-olive/80' },
                { h: 38, cls: 'bg-gradient-to-b from-olive to-olive-d' },
                { h: 28, cls: 'bg-olive/80' },
                { h: 14, cls: 'bg-olive/60' },
                { h: 20, cls: 'bg-olive/30' },
              ].map((bar, i) => (
                <span
                  key={i}
                  className={`w-1 rounded-full ${bar.cls}`}
                  style={{ height: bar.h }}
                />
              ))}
            </div>
            <p className="mt-4 text-4xl font-black leading-none tracking-tight">
              Agro
              <span className="bg-gradient-to-b from-olive to-olive-d bg-clip-text text-transparent">
                Voz
              </span>
            </p>
            <p className="mt-2.5 text-sm text-ink">Cuaderno de campo por voz</p>
          </div>

          <h1 className="text-center text-lg font-bold">
            {method === 'signup' ? 'Crear cuenta de prueba' : 'Iniciar sesión'}
          </h1>

          {/* Tabs: pick how to sign in. Hidden in signup mode, which is its own
              flow reached from the link below. */}
          {method !== 'signup' && (
            <div className="mt-5 grid grid-cols-2 rounded-xl border border-line bg-card p-1 text-sm font-semibold">
              <button
                type="button"
                onClick={() => switchMethod('code')}
                className={`rounded-lg py-2 transition ${
                  method === 'code' ? 'bg-olive text-white shadow-card' : 'text-ink hover:bg-olive/5'
                }`}
              >
                Código
              </button>
              <button
                type="button"
                onClick={() => switchMethod('password')}
                className={`rounded-lg py-2 transition ${
                  method === 'password' ? 'bg-olive text-white shadow-card' : 'text-ink hover:bg-olive/5'
                }`}
              >
                Contraseña
              </button>
            </div>
          )}

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
                className="mt-5 w-full rounded-xl border border-line bg-card px-4 py-3 text-base outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
              />

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
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
                className="mt-5 w-full rounded-xl border border-line bg-card px-4 py-3 text-center text-2xl tracking-[0.4em] outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
              />

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
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
                className="mt-4 w-full text-sm font-semibold text-olive hover:underline"
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
                className="mt-5 w-full rounded-xl border border-line bg-card px-4 py-3 text-base outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
              />

              <input
                type="password"
                required
                autoComplete="current-password"
                placeholder="Contraseña"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-3 w-full rounded-xl border border-line bg-card px-4 py-3 text-base outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
              />

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
              >
                {status === 'sending' ? 'Entrando…' : 'Entrar'}
              </button>

              <p className="mt-4 text-center text-xs leading-relaxed text-ink">
                ¿No tienes contraseña? Entra con un código y créala en Ajustes.
              </p>
            </form>
          )}

          {/* Signup, step 1: email -> send code. Same OTP form as login, but it
              creates the account (shouldCreateUser) and, after verifying, App
              provisions a demo advisor + sandbox so the field flow works. */}
          {method === 'signup' && !codeSent && (
            <form onSubmit={requestCode} className="mt-5">
              <p className="text-center text-sm leading-relaxed text-ink">
                Introduce tu correo y te enviaremos un código para crear tu cuenta
                de prueba con datos de demostración.
              </p>

              <input
                type="email"
                required
                autoComplete="email"
                inputMode="email"
                placeholder="tu@correo.es"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-5 w-full rounded-xl border border-line bg-card px-4 py-3 text-base outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
              />

              {/* Turnstile widget mounts here once activated (see getCaptchaToken). */}

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
              >
                {status === 'sending' ? 'Enviando…' : 'Crear cuenta'}
              </button>
            </form>
          )}

          {/* Signup, step 2: verify the code (same as login's code step). The
              copy is deliberately generic ("continuar", not "crear"): with
              shouldCreateUser, Supabase silently sends a LOGIN code when the
              email already has an account, and we cannot tell which case we are
              in without leaking whether an email is registered — so the text
              covers both. */}
          {method === 'signup' && codeSent && (
            <form onSubmit={verifyCode} className="mt-5">
              <p className="text-center text-sm leading-relaxed text-ink">
                Hemos enviado un código a{' '}
                <span className="font-semibold text-soil">{email}</span>.
                Introdúcelo para continuar: crearemos tu cuenta de prueba o, si
                tu correo ya tenía una, iniciaremos sesión con ella
                automáticamente.
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
                className="mt-5 w-full rounded-xl border border-line bg-card px-4 py-3 text-center text-2xl tracking-[0.4em] outline-none transition focus:border-olive focus:ring-2 focus:ring-olive/15"
              />

              {error && <p className="mt-3 text-sm text-terra">{error}</p>}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="mt-4 w-full rounded-xl bg-olive py-3 font-bold text-white shadow-card transition hover:bg-olive-d active:scale-[0.98] disabled:opacity-60"
              >
                {status === 'sending' ? 'Entrando…' : 'Continuar'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setCodeSent(false)
                  setCode('')
                  setError(null)
                }}
                className="mt-4 w-full text-sm font-semibold text-olive hover:underline"
              >
                Usar otro correo
              </button>
            </form>
          )}

          {/* Turnstile captcha — one widget for the whole screen (Supabase's
              captcha is project-wide). Kept mounted so its instance is stable,
              but hidden on the code-verify step, which Supabase does not gate. */}
          {CAPTCHA_ACTIVE && (
            <div className={`mt-5 flex justify-center ${codeSent ? 'hidden' : ''}`}>
              <div ref={captchaRef} />
            </div>
          )}

          {/* Entry/exit between login and signup — only when the hackathon flag
              is on. Off by default: the screen is login-only. */}
          {SIGNUP_ENABLED && (
            <button
              type="button"
              onClick={() => switchMethod(method === 'signup' ? 'code' : 'signup')}
              className="mt-6 w-full text-center text-sm font-semibold text-olive hover:underline"
            >
              {method === 'signup'
                ? 'Ya tengo cuenta · Iniciar sesión'
                : '¿Eres nuevo? Crea una cuenta de prueba'}
            </button>
          )}

          {/* RGPD consent line — one line covers every way in (code, password,
              signup); the actual notice lives at /privacidad. */}
          <p className="mt-6 text-center text-xs leading-relaxed text-ink/70">
            Al continuar aceptas la{' '}
            <Link to="/privacidad" className="font-semibold text-olive underline">
              política de privacidad
            </Link>
            .
          </p>
        </div>
      </main>
    </div>
  )
}

export default Login
