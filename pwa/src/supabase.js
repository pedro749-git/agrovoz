import { createClient } from '@supabase/supabase-js'

// One Supabase client for the whole app, built from PUBLIC values only.
// Vite replaces `import.meta.env.VITE_*` with the literal string at build time,
// so anything referenced here ends up in the browser bundle — never a secret.
// The publishable key is designed for exactly this (public client auth).
const url = import.meta.env.VITE_SUPABASE_URL
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

// Fail loudly at startup instead of a confusing 401 later: a missing key means
// .env.local was not filled in.
if (!url || !publishableKey) {
  throw new Error(
    'Faltan VITE_SUPABASE_URL o VITE_SUPABASE_PUBLISHABLE_KEY. ' +
      'Copia .env.example a .env.local y rellena los valores del proyecto Supabase.',
  )
}

export const supabase = createClient(url, publishableKey, {
  auth: {
    // Keep the session in localStorage so a reload (or reopening the installed
    // PWA) stays logged in...
    persistSession: true,
    // ...and silently renew the short-lived access token before it expires, so
    // the advisor is not kicked out mid-shift.
    autoRefreshToken: true,
    // After the user clicks the magic link, Supabase returns to the app with
    // the token in the URL; the SDK reads it, stores the session and cleans the
    // address bar — all automatically.
    detectSessionInUrl: true,
  },
})
