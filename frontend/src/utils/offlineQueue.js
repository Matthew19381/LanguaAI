/**
 * Offline practice: a downloaded exercise pack + an outbox of answers.
 *
 * Offline the device grades locally and queues the result; on reconnect the
 * queue is replayed to the server, which applies FSRS scheduling. Each queued
 * answer carries a UUID so a retried replay cannot count the review twice.
 */

const PACK_KEY = 'offlinePack'
const QUEUE_KEY = 'offlineQueue'

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

export function queueSize() {
  return getQueue().length
}

export function clearQueue() {
  localStorage.removeItem(QUEUE_KEY)
}

/**
 * Replay queued answers. Events that reach the server (including duplicates it
 * rejects) are removed; genuine network failures are kept for the next attempt.
 * Returns { synced, failed }.
 */
export async function syncQueue(postAnswer) {
  const pending = getQueue()
  if (pending.length === 0) return { synced: 0, failed: 0 }

  const remaining = []
  let synced = 0

  for (const event of pending) {
    try {
      await postAnswer(event)
      synced += 1
    } catch (err) {
      const status = err?.response?.status
      if (status && status >= 400 && status < 500) {
        // The server rejected it permanently (deleted exercise, bad payload) —
        // retrying forever would block the queue.
        continue
      }
      remaining.push(event)
    }
  }

  writeQueue(remaining)
  return { synced, failed: remaining.length }
}
