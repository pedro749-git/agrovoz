import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { supabase } from './supabase.js'
import ConfirmDialog from './ConfirmDialog.jsx'
import Icon from './Icon.jsx'

// The app's main navigation: a floating rounded bar at the bottom — thumb
// reach for a phone held one-handed in the field — with a raised home button
// in the centre. Five slots: Historial · Validar · (Inicio) · Ajustes · Salir.
//
// The centre button only NAVIGATES to Home; the big record button lives on the
// Home screen itself. It wears a house icon, not a mic, precisely so it cannot
// be mistaken for a record control.
//
// "Salir" lives in the thumb zone, so it signs out behind a confirmation
// dialog: one stray tap must not log the advisor out in the middle of a field.
function Tab({ icon, label, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-current={active ? 'page' : undefined}
      className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-2xl py-1.5 transition active:scale-90 ${
        active ? 'bg-white/12 text-white' : 'text-white/60 hover:text-white/85'
      }`}
    >
      <Icon name={icon} className="h-[21px] w-[21px]" />
      <span className="text-[9px] font-bold tracking-wide">{label}</span>
    </button>
  )
}

function BottomNav() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [confirmLogout, setConfirmLogout] = useState(false)

  return (
    <>
      <nav className="fixed inset-x-0 bottom-0 z-20 flex justify-center px-4 pb-safe">
        <div className="mb-3 flex w-full max-w-md items-center rounded-full bg-gradient-to-b from-[#47562a] to-olive-d px-2.5 py-1.5 shadow-float">
          <Tab
            icon="calendar"
            label="Historial"
            active={pathname === '/historial'}
            onClick={() => navigate('/historial')}
          />
          <Tab
            icon="shield-check"
            label="Validar"
            active={pathname === '/validaciones'}
            onClick={() => navigate('/validaciones')}
          />

          {/* Centre home button, raised half out of the bar. The bone ring
              cuts it out against both the bar and the page behind it. */}
          <div className="relative mx-1 -mt-8 flex h-16 w-16 shrink-0 items-center justify-center">
            <button
              type="button"
              onClick={() => navigate('/')}
              aria-label="Inicio"
              aria-current={pathname === '/' ? 'page' : undefined}
              className="relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-b from-olive to-olive-d text-white shadow-float ring-4 ring-bone transition hover:brightness-95 active:scale-95"
            >
              <Icon name="home" className="h-7 w-7" />
            </button>
          </div>

          <Tab
            icon="settings"
            label="Ajustes"
            active={pathname === '/ajustes'}
            onClick={() => navigate('/ajustes')}
          />
          <Tab icon="log-out" label="Salir" onClick={() => setConfirmLogout(true)} />
        </div>
      </nav>

      <ConfirmDialog
        open={confirmLogout}
        title="¿Cerrar sesión?"
        body="Para volver a entrar necesitarás tu correo (código o contraseña)."
        confirmLabel="Salir"
        onConfirm={() => supabase.auth.signOut()}
        onCancel={() => setConfirmLogout(false)}
      />
    </>
  )
}

export default BottomNav
