import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  // Expose the dev server on the local network (0.0.0.0) so the phone,
  // on the same Wi-Fi, can reach it at http://<your-ip>:5173
  server: {
    host: true,
    // Accept any Host header: the cloudflared tunnel forwards requests with a
    // *.trycloudflare.com host that changes every run. Safe here — this is the
    // dev server only, run locally and shut down after use.
    allowedHosts: true,
    // Forward the app's API calls to the FastAPI backend. The browser then sees
    // a SINGLE origin (the Vite dev server / tunnel), so there is no CORS to
    // configure: phone -> tunnel -> Vite -> proxy -> localhost:8000.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    // Turns the app into an installable PWA: generates the service worker
    // and the web manifest (the metadata Android uses when you "Add to home screen").
    VitePWA({
      registerType: 'autoUpdate', // a new build silently replaces the old one
      injectRegister: 'auto', // auto-inject the service-worker registration, no manual code
      manifest: {
        name: 'Agrovoz — Cuaderno GIP',
        short_name: 'Agrovoz',
        description: 'Registro fitosanitario por voz para asesores GIP',
        lang: 'es',
        theme_color: '#3c4a22', // brand dark olive: the app bar colour once installed
        background_color: '#f5f2ea', // warm paper, matches the app background
        display: 'standalone', // launches like a native app (no browser chrome)
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable', // lets Android crop the icon to its shape
          },
        ],
      },
      // Enable the service worker in `npm run dev` too, so we can test the
      // install flow on the phone without a production build.
      devOptions: {
        enabled: true,
      },
    }),
  ],
})
