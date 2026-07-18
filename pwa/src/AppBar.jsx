import Icon from './Icon.jsx'

// The shared top chrome. With the main actions moved to the bottom bar
// (BottomNav), the old full-width olive bar became a "hanging pill": the
// section name in a centred capsule that hangs from the top edge — flat on
// top, rounded at the bottom — in the brand olive. Stacked screens (Detalle,
// Corregir, Privacidad) pass `onBack` and get a round floating back button on
// the left. Nothing paints a full-width background any more, so content
// scrolls behind the pill; its shadow keeps it legible.
function AppBar({ title, subtitle, onBack }) {
  return (
    <header className="pointer-events-none sticky top-0 z-10 pt-safe">
      <div className="relative flex justify-center px-4">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            aria-label="Volver"
            className="pointer-events-auto absolute left-4 top-1 flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-b from-[#47562a] to-olive-d text-white shadow-float transition hover:brightness-110 active:scale-90"
          >
            <Icon name="chevron-left" className="h-5 w-5" />
          </button>
        )}

        <div className="pointer-events-auto flex max-w-[calc(100%-7rem)] flex-col items-center rounded-b-[24px] bg-gradient-to-b from-[#47562a] to-olive-d px-7 pb-2.5 pt-2 text-center text-white shadow-float">
          <div className="w-full truncate text-[14px] font-bold leading-tight tracking-wide">
            {title}
          </div>
          {subtitle && (
            <div className="w-full truncate text-[10px] leading-tight text-white/60">
              {subtitle}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default AppBar
