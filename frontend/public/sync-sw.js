/* Background Sync: replay the offline outbox while the app is closed.
 *
 * Imported into the workbox-generated service worker via workbox.importScripts
 * (like push-sw.js). Runs in the SW global scope, so it is self-contained — it
 * cannot import app modules. The IndexedDB store and the replay mapping mirror
 * outboxDB.js / offlineQueue.js (replayRequestFor); change them together.
 *
 * The page's useOfflineSync still drains the localStorage outbox when the app is
 * open; this handler covers the "app fully closed, network came back" case on
 * browsers that support the Background Sync API (Chromium). */

const OUTBOX_DB = 'linguaai'
const OUTBOX_STORE = 'outbox'
const OUTBOX_SYNC_TAG = 'linguaai-outbox'

function outboxOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(OUTBOX_DB, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(OUTBOX_STORE)) {
        db.createObjectStore(OUTBOX_STORE, { keyPath: 'client_event_id' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

function outboxGetAll(db) {
  return new Promise((resolve, reject) => {
    const r = db.transaction(OUTBOX_STORE, 'readonly').objectStore(OUTBOX_STORE).getAll()
    r.onsuccess = () => resolve(r.result || [])
    r.onerror = () => reject(r.error)
  })
}

function outboxDelete(db, id) {
  return new Promise((resolve, reject) => {
    const r = db.transaction(OUTBOX_STORE, 'readwrite').objectStore(OUTBOX_STORE).delete(id)
    r.onsuccess = () => resolve()
    r.onerror = () => reject(r.error)
  })
}

// Mirror of offlineQueue.replayRequestFor — keep in sync.
function replayRequestFor(event) {
  switch (event.kind) {
    case 'exercise_answer':
      return {
        url: `/api/exercises/${event.exercise_id}/answer`,
        body: { user_id: event.user_id, answer: event.answer, client_event_id: event.client_event_id, answered_at: event.answered_at },
      }
    case 'flashcard_review':
      return {
        url: `/api/flashcards/${event.flashcard_id}/review?user_id=${event.user_id}`,
        body: { rating: event.rating, client_event_id: event.client_event_id, reviewed_at: event.reviewed_at },
      }
    case 'lesson_complete':
      return {
        url: `/api/lessons/${event.lesson_id}/complete`,
        body: { user_id: event.user_id, client_event_id: event.client_event_id, completed_at: event.completed_at },
      }
    default:
      return null
  }
}

async function replayOutbox() {
  const db = await outboxOpen()
  const events = await outboxGetAll(db)
  let retryNeeded = false

  for (const event of events) {
    const spec = replayRequestFor(event)
    if (!spec) {
      await outboxDelete(db, event.client_event_id) // unknown kind — don't block
      continue
    }
    try {
      const res = await fetch(spec.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin', // carry the access-gate cookie
        body: JSON.stringify(spec.body),
      })
      if (res.ok || (res.status >= 400 && res.status < 500)) {
        // Delivered, or permanently rejected — either way stop retrying it.
        await outboxDelete(db, event.client_event_id)
      } else {
        retryNeeded = true // 5xx — keep it, let the browser retry the sync
      }
    } catch {
      retryNeeded = true // network still down — keep it for the next sync
    }
  }

  db.close()
  // Rejecting tells the browser to fire the sync again later with backoff.
  if (retryNeeded) throw new Error('outbox-sync-incomplete')
}

self.addEventListener('sync', (event) => {
  if (event.tag === OUTBOX_SYNC_TAG) {
    event.waitUntil(replayOutbox())
  }
})
