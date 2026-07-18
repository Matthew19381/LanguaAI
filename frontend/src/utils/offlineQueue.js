/**
 * Offline practice: a downloaded exercise pack + an outbox of answers.
 *
 * Offline the device grades locally and queues the result; on reconnect the
 * queue is replayed to the server, which applies FSRS scheduling. Each queued
 * answer carries a UUID so a retried replay cannot count the review twice.
 */

const PACK_KEY = 'offlinePack'            // exercises
const CARD_PACK_KEY = 'offlineCardPack'   // flashcards
const QUEUE_KEY = 'offlineQueue'          // shared outbox (events carry `kind`)

export const KIND_EXERCISE = 'exercise_answer'
export const KIND_FLASHCARD = 'flashcard_review'

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
        continue
      }
      remaining.push(event)
    }
  }

  writeQueue(remaining)
  return { synced, failed: remaining.length }
}
