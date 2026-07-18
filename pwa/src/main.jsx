import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
// Brand typeface (Manrope, variable weight), bundled with the app — no font
// CDN: the PWA must keep its face offline in the field. Registered as
// --font-sans in index.css.
import '@fontsource-variable/manrope'
import './index.css'
import App from './App.jsx'

// HashRouter (routes after #) instead of BrowserRouter: the PWA is served as
// static files with no SPA fallback, so reloading/sharing a deep link like
// /registro/:id would 404 under BrowserRouter. The hash keeps every route
// client-side. Switch to BrowserRouter once the host rewrites unknown paths to
// index.html.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
)
