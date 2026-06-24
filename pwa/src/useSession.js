import { useEffect, useState } from 'react'
import { supabase } from './supabase.js'

// React hook that exposes the current Supabase auth session.
//
//   session === null  -> logged out (show the login screen)
//   session === {...}  -> logged in (the object carries the access token / JWT)
//   loading === true   -> we are still reading the stored session; show nothing
//                         yet so the login screen does not flash for a returning
//                         user who is actually already authenticated.
export function useSession() {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 1) Read whatever session is already persisted (page reload / app reopen).
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })

    // 2) Then stay in sync: this fires on login, logout AND token refresh, so
    //    the JWT we hand to the API is always the current one.
    const { data } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession)
    })

    // Stop listening when the component unmounts (prevents leaks / double subs).
    return () => data.subscription.unsubscribe()
  }, [])

  return { session, loading }
}
