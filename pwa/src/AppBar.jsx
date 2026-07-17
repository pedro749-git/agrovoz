import Icon from './Icon.jsx'

// The shared top bar, so every screen wears the same olive header (brand colour
// from the prototype) with consistent spacing, a hairline shadow and safe-area
// padding for the notch. Screens compose it three ways:
//   - a title + optional subtitle (Home, Ajustes)
//   - a back chevron + title (Detalle, Validaciones)  -> pass `onBack`
//   - a cluster of icon buttons on the right           -> pass `actions`
//
// A subtle top-to-bottom darkening gives the bar depth without a heavy border;
// the hairline shadow separates it from the paper background as content scrolls.
function AppBar({ title, subtitle, onBack, actions }) {
  return (
    <header className="sticky top-0 z-10 bg-gradient-to-b from-[#47562a] to-olive-d px-4 pb-3 pt-safe text-white shadow-[0_1px_0_rgb(0_0_0/0.12),0_6px_16px_-10px_rgb(0_0_0/0.5)]">
      <div className="flex items-center gap-3 pt-3">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            aria-label="Volver"
            className="-ml-1.5 flex h-9 w-9 items-center justify-center rounded-full transition hover:bg-white/10 active:scale-90 active:bg-white/10"
          >
            <Icon name="chevron-left" className="h-6 w-6" />
          </button>
        )}

        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-semibold leading-tight tracking-wide">
            {title}
          </div>
          {subtitle && (
            <div className="truncate text-[11px] leading-tight text-white/60">{subtitle}</div>
          )}
        </div>

        {actions && <div className="flex items-center gap-1">{actions}</div>}
      </div>
    </header>
  )
}

// A round icon-only button for the AppBar's right cluster (Validaciones, Ajustes,
// Salir). `title` doubles as the accessible label and the long-press tooltip.
export function BarButton({ icon, title, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      className="flex h-9 w-9 items-center justify-center rounded-full text-white/85 transition hover:bg-white/10 active:scale-90 active:bg-white/10"
    >
      <Icon name={icon} className="h-[18px] w-[18px]" />
    </button>
  )
}

export default AppBar
