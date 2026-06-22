function App() {
  return (
    // Outer layer: full visible height + safe-area padding (keeps content off
    // the notch and the bottom gesture bar). No design padding here.
    <main className="flex min-h-dvh flex-col items-center justify-center bg-green-50 p-safe">
      {/* Inner layer: the actual design padding and content. */}
      <div className="flex flex-col items-center gap-4 p-6 text-center">
        <h1 className="text-4xl font-bold text-green-800">Agrovoz</h1>
        <p className="text-gray-600">Cuaderno fitosanitario por voz</p>
        <span className="rounded-full bg-green-700 px-5 py-2 font-medium text-white shadow">
          PWA lista ✓
        </span>
      </div>
    </main>
  )
}

export default App
