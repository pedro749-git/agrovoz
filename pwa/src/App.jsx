import Recorder from './Recorder.jsx'

function App() {
  return (
    // Full-height screen with the paper-like background and dark soil text.
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      {/* Top bar (prototype `.topbar`): dark olive, fills behind the notch.
          `pt-safe` pushes its content below the notch; the olive background
          still paints up into the safe area. */}
      <header className="bg-olive-d px-4 pb-3 text-white pt-safe">
        <div className="flex items-center gap-3 pt-3">
          {/* Burger icon (three bars) — purely visual for now. */}
          <div className="flex flex-col gap-[3px]">
            <span className="h-0.5 w-4 rounded bg-white" />
            <span className="h-0.5 w-4 rounded bg-white" />
            <span className="h-0.5 w-4 rounded bg-white" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-wide">AgroVoz</div>
            <div className="text-[10px] opacity-70">Cuaderno de campo por voz</div>
          </div>
        </div>
      </header>

      {/* Center area: the record button. `flex-1` makes it fill the space
          between the top bar and the bottom safe area. */}
      <main className="flex flex-1 flex-col items-center justify-center px-6 pb-safe">
        <Recorder />
      </main>
    </div>
  )
}

export default App
