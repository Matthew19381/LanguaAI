/**
 * Offline practice: a downloaded exercise pack + an outbox of answers.
 *
 * Offline the device grades locally and queues the result; on reconnect the
 * queue is replayed to the server, which applies FSRS scheduling. Each queued
 * answer carries a UUID so a retried replay cannot count the review twice.
 *
 * The outbox lives in localStorage and is drained by useOfflineSync when the app
 * is open (online / focus). Every event is ALSO mirrored to IndexedDB so the
 * service worker can replay it via the Background Sync API while the app is
 * closed — see outboxDB.js and public/sync-sw.js.
 */
import { mirrorPut, mirrorDelete, requestBackgroundSync } from './outboxDB'

const PACK_KEY = 'offlinePack'            // exercises
const CARD_PACK_KEY = 'offlineCardPack'   // flashcards
const QUEUE_KEY = 'offlineQueue'          // shared outbox (events carry `kind`)

export const KIND_EXERCISE = 'exercise_answer'
export const KIND_FLASHCARD = 'flashcard_review'
export const KIND_LESSON = 'lesson_complete'

/** Mirror a freshly queued event to IndexedDB and ask for a background sync.
 * Best-effort and non-blocking so enqueue stays synchronous. */
function afterEnqueue(event) {
  mirrorPut(event)
  requestBackgroundSync()
}

// ── Local grading ───────────────────────────────────────────────────────────
// Must mirror grade_answer() in backend/services/exercise_service.py, which does
//   re.sub(r"[^\w\s]", "", s.strip().lower())  and compares for equality.
// Python's \w is Unicode-aware, JavaScript's is ASCII-only — so we use explicit
// Unicode classes here, otherwise "schön" and "Å¼Ã³Å‚w" would grade differently
// on the device than on the server.
const PUNCT = /[^\p{L}\p{N}_\s]/gu

export function normalizeAnswer(text) {
  return (text || '').trim().toLowerCase().replace(PUNCT, '')
}

export function gradeLocally(expected, given) {
  const e = normalizeAnswer(expected)
  return e.length > 0 && e === normalizeAnswer(given)
}

// ── Pack storage ────────────────────────────────────────────────────────────

export function savePack(pack) {
  try {
    localStorage.setItem(PACK_KEY, JSON.stringify(pack))
    return true
  } catch {
    return false // quota exceeded — offline practice simply stays unavailable
  }
}

export function loadPack() {
  try {
    const raw = localStorage.getItem(PACK_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearPack() {
  localStorage.removeItem(PACK_KEY)
}

// ── Flashcard pack ──────────────────────────────────────────────────────────

export function saveCardPack(pack) {
  try {
    localStorage.setItem(CARD_PACK_KEY, JSON.stringify(pack))
    return true
  } catch {
    return false
  }
}

export function loadCardPack() {
  try {
    const raw = localStorage.getItem(CARD_PACK_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearCardPack() {
  localStorage.removeItem(CARD_PACK_KEY)
}

// ── Outbox ──────────────────────────────────────────────────────────────────

function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `evt-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function getQueue() {
  try {
    const raw = localStorage.getItem(QUEUE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeQueue(items) {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(items))
  } catch {
    /* full storage: keep the in-memory result, drop persistence */
  }
}

export function enqueueAnswer({ exerciseId, userId, answer, correct }) {
  const event = {
    kind: KIND_EXERCISE,
    client_event_id: newId(),
    exercise_id: exerciseId,
    user_id: userId,
    answer,
    correct,
    answered_at: new Date().toISOString(),
  }
  writeQueue([...getQueue(), event])
  afterEnqueue(event)
  return event
}

export function enqueueLessonComplete({ lessonId, userId }) {
  const event = {
    kind: KIND_LESSON,
    client_event_id: newId(),
    lesson_id: lessonId,
    user_id: userId,
    completed_at: new Date().toISOString(),
  }
  writeQueue([...getQueue(), event])
  afterEnqueue(event)
  return event
}

export function enqueueFlashcardReview({ flashcardId, userId, rating }) {
  const event = {
    kind: KIND_FLASHCARD,
    client_event_id: newId(),
    flashcard_id: flashcardId,
    user_id: userId,
    rating,
    reviewed_at: new Date().toISOString(),
  }
  writeQueue([...getQueue(), event])
  afterEnqueue(event)
  return event
}

/** How many queued events of a given kind (omit for the whole outbox). */
export function pendingByKind(kind) {
  const q = getQueue()
  if (!kind) return q.length
  return q.filter(e => (e.kind || KIND_EXERCISE) === kind).length
}

export function queueSize() {
  return getQueue().length
}

export function clearQueue() {
  localStorage.removeItem(QUEUE_KEY)
}

/**
 * Replay every queued event through the handler matching its `kind`.
 *
 * `handlers` maps kind → async fn(event). Events that reach the server
 * (including ones it rejects permanently) are removed; genuine network failures
 * stay queued for the next attempt. Returns { synced, failed }.
 */
export async function syncQueue(handlers) {
  const pending = getQueue()
  if (pending.length === 0) return { synced: 0, failed: 0 }

  const remaining = []
  let synced = 0

  for (let i = 0; i < pending.length; i++) {
    const event = pending[i]
    // Events queued by an older build predate `kind` and were always exercises
    const handler = handlers[event.kind || KIND_EXERCISE]
    if (!handler) {
      // Unknown kind (e.g. downgraded app) — drop it rather than block the queue
      continue
    }
    try {
      await handler(event)
      synced += 1
      mirrorDelete(event.client_event_id)  // keep the IndexedDB mirror in step
    } catch (err) {
      // The API client wraps errors, so read the status from either shape
      const status = err?.response?.status ?? err?.status
      if (status === 401) {
        // Gated and locked — stop and keep this event *and everything after it*,
        // since the rest would only produce more 401s.
        remaining.push(...pending.slice(i))
        break
      }
      if (status && status >= 400 && status < 500) {
        // Permanently rejected (deleted card, bad payload) — retrying forever
        // would block everything behind it.
        mirrorDelete(event.client_event_id)
        continue
      }
      remaining.push(event)
    }
  }

  writeQueue(remaining)
  return { synced, failed: remaining.length }
}

/**
 * Map a queued event to the HTTP request that replays it. Pure and exported so
 * it can be unit-tested. **public/sync-sw.js keeps an identical copy** (a service
 * worker cannot import app modules) — change both together.
 */
export function replayRequestFor(event) {
  switch (event.kind) {
    case KIND_EXERCISE:
      return {
        url: `/api/exercises/${event.exercise_id}/answer`,
        body: {
          user_id: event.user_id,
          answer: event.answer,
          client_event_id: event.client_event_id,
          answered_at: event.answered_at,
        },
      }
    case KIND_FLASHCARD:
      return {
        url: `/api/flashcards/${event.flashcard_id}/review?user_id=${event.user_id}`,
        body: {
          rating: event.rating,
          client_event_id: event.client_event_id,
          reviewed_at: event.reviewed_at,
        },
      }
    case KIND_LESSON:
      return {
        url: `/api/lessons/${event.lesson_id}/complete`,
        body: {
          user_id: event.user_id,
          client_event_id: event.client_event_id,
          completed_at: event.completed_at,
        },
      }
    default:
      return null
  }
}
