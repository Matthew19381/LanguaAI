import { useState, useEffect, useCallback } from 'react'
import { replayAnswer, replayFlashcardReview, replayLessonComplete } from '../api/client'
import { syncQueue, queueSize, KIND_EXERCISE, KIND_FLASHCARD, KIND_LESSON } from '../utils/offlineQueue'

const HANDLERS = {
  [KIND_EXERCISE]: replayAnswer,
  [KIND_FLASHCARD]: replayFlashcardReview,
  [KIND_LESSON]: replayLessonComplete,
}

/**
 * Drains the offline outbox — exercise answers and flashcard reviews alike.
 *
 * Mounted app-wide (Layout), so work done offline on any screen syncs as soon as
 * the connection returns, regardless of which page the user happens to open.
 */
export function useOfflineSync() {
  const [pending, setPending] = useState(queueSize())
  const [syncing, setSyncing] = useState(false)
  const [lastSynced, setLastSynced] = useState(0)

  const sync = useCallback(async () => {
    if (queueSize() === 0 || !navigator.onLine) return
    setSyncing(true)
    try {
      const { synced } = await syncQueue(HANDLERS)
      setPending(queueSize())
      if (synced > 0) setLastSynced(synced)
    } finally {
      setSyncing(false)
    }
  }, [])

  useEffect(() => {
    sync()
    const onOnline = () => sync()
    // Other screens push to the queue; keep the badge honest without polling hard
    const onFocus = () => setPending(queueSize())
    window.addEventListener('online', onOnline)
    window.addEventListener('focus', onFocus)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('focus', onFocus)
    }
  }, [sync])

  return { pending, syncing, lastSynced, sync, refresh: () => setPending(queueSize()) }
}
