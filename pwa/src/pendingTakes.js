// Local queue for recordings that could not reach the server (no coverage in
// the field). Each entry keeps EXACTLY what a retry must reuse — the audio blob
// plus the transactionId / deviceTimestamp captured when the recording stopped —
// so a take dictated offline at 10:00 and synced at 18:00 still carries the
// 10:00 device clock (hard rule 2) and cannot duplicate on retry (hard rule 3).
//
// IndexedDB and not localStorage because it is the only browser store that
// accepts blobs. It is BEST-EFFORT storage: Safari may evict it after ~7 days
// without using the app, so this is a same-day sync buffer, not an archive.
// Losing or discarding an entry loses nothing legal — a pending take was never
// persisted server-side, so hard rule 1 (never delete legal records) does not
// apply here.

const DB_NAME = 'agrovoz'
const STORE = 'pending_takes'

// Opens (and on first use creates) the database. IndexedDB is callback-based;
// wrapping it in a Promise lets the rest of the module use plain async/await.
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () =>
      request.result.createObjectStore(STORE, { keyPath: 'transactionId' })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

// Runs one operation inside a transaction and resolves when the transaction
// COMMITS — not merely when the request succeeds, because commit is what
// guarantees the audio actually reached disk before we clear it from memory.
async function withStore(mode, operation) {
  const db = await openDb()
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode)
      const request = operation(tx.objectStore(STORE))
      tx.oncomplete = () => resolve(request.result)
      tx.onerror = () => reject(tx.error)
      tx.onabort = () => reject(tx.error)
    })
  } finally {
    db.close()
  }
}

// `put` (upsert keyed by transactionId) makes queueing idempotent: re-queueing
// the same take after another failed retry overwrites its entry, never
// duplicates it.
export function savePending({ blob, transactionId, deviceTimestamp }) {
  return withStore('readwrite', (store) =>
    store.put({
      transactionId,
      blob,
      deviceTimestamp,
      queuedAt: new Date().toISOString(),
    }),
  )
}

// Oldest first, so the advisor clears the backlog in dictation order.
export async function listPending() {
  const takes = await withStore('readonly', (store) => store.getAll())
  return takes.sort((a, b) => a.deviceTimestamp.localeCompare(b.deviceTimestamp))
}

// Deleting a missing key is a no-op in IndexedDB, so callers may clean up
// without checking whether the take was ever queued.
export function deletePending(transactionId) {
  return withStore('readwrite', (store) => store.delete(transactionId))
}
