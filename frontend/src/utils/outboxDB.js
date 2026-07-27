/**
 * IndexedDB mirror of the offline outbox, plus Background Sync registration.
 *
 * Why a mirror: the page-driven sync (useOfflineSync) replays from localStorage,
 * but a service worker cannot read localStorage. To replay work while the app is
 * fully closed (Background Sync API), the SW needs the queue in IndexedDB. So on
 * every enqueue we ALSO write the event here and ask the browser for a sync.
 *
 * Double-replay (page AND SW) is harmless: every event carries a client_event_id
 * and the backend is idempotent, so the second replay is a no-op ("duplicate").
 * Each side deletes what it has replayed from its own store.
 *
 * All functions are best-effort and never throw — if IndexedDB or Background Sync
 * is unavailable (older browsers, Firefox/Safari for sync), the app simply falls
 * back to the existing online/focus sync.
 */

const DB_NAME = 'linguaai'
const STORE = 'outbox'
export const SYNC_TAG = 'linguaai-outbox'

function openDB() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('no-indexeddb'))
      return
    }
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'client_event_id' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error || new Error('idb-open-failed'))
  })
}

function tx(db, mode) {
  return db.transaction(STORE, mode).objectStore(STORE)
}

/** Mirror one queued event into IndexedDB. Best-effort. */
export async function mirrorPut(event) {
  if (!event || !event.client_event_id) return
  try {
    const db = await openDB()
    await new Promise((res, rej) => {
      const r = tx(db, 'readwrite').put(event)
      r.onsuccess = res
      r.onerror = () => rej(r.error)
    })
    db.close()
  } catch {
    /* IndexedDB unavailable — page-driven sync still covers this event */
  }
}

/** All mirrored events (used by the service worker's sync handler). */
export async function mirrorGetAll() {
  try {
    const db = await openDB()
    const all = await new Promise((res, rej) => {
      const r = tx(db, 'readonly').getAll()
      r.onsuccess = () => res(r.result || [])
      r.onerror = () => rej(r.error)
    })
    db.close()
    return all
  } catch {
    return []
  }
}

/** Remove a mirrored event once it has been replayed (by either side). */
export async function mirrorDelete(clientEventId) {
  if (!clientEventId) return
  try {
    const db = await openDB()
    await new Promise((res, rej) => {
      const r = tx(db, 'readwrite').delete(clientEventId)
      r.onsuccess = res
      r.onerror = () => rej(r.error)
    })
    db.close()
  } catch {
    /* ignore */
  }
}

/** Ask the browser to replay the outbox in the background when it can.
 * No-op where Background Sync is unsupported (Firefox, Safari, iOS). */
export async function requestBackgroundSync() {
  try {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return
    if (typeof window === 'undefined' || !('SyncManager' in window)) return
    const reg = await navigator.serviceWorker.ready
    await reg.sync.register(SYNC_TAG)
  } catch {
    /* registration failed — online/focus sync remains the fallback */
  }
}
