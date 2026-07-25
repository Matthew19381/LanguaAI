import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  gradeLocally, normalizeAnswer, savePack, loadPack, clearPack,
  saveCardPack, loadCardPack, clearCardPack,
  enqueueAnswer, enqueueFlashcardReview, enqueueLessonComplete, pendingByKind,
  getQueue, queueSize, clearQueue, syncQueue,
  KIND_EXERCISE, KIND_FLASHCARD, KIND_LESSON,
} from '../offlineQueue'

// Handlers map used by most sync tests
const handlers = (exercise = vi.fn(), flashcard = vi.fn(), lesson = vi.fn()) => ({
  [KIND_EXERCISE]: exercise,
  [KIND_FLASHCARD]: flashcard,
  [KIND_LESSON]: lesson,
})

beforeEach(() => {
  localStorage.clear()
})

describe('local grading parity with the server', () => {
  // These cases mirror backend/tests/test_offline_sync.py::
  // test_grading_rules_used_by_offline_clients — if one side changes, both fail.
  it('ignores case, surrounding space and punctuation', () => {
    expect(gradeLocally('Ich sehe den Hund', 'ich sehe den hund!')).toBe(true)
    expect(gradeLocally('habe', '  HABE  ')).toBe(true)
  })

  it('treats diacritics as significant', () => {
    expect(gradeLocally('schön', 'schon')).toBe(false)
  })

  it('keeps non-ASCII letters instead of stripping them', () => {
    // A JS-default \w would delete these and make everything compare equal
    expect(gradeLocally('żółw', 'żółw')).toBe(true)
    expect(normalizeAnswer('żółw!')).toBe('żółw')
    expect(normalizeAnswer('schön.')).toBe('schön')
  })

  it('rejects wrong answers and empty expectations', () => {
    expect(gradeLocally('habe', 'hast')).toBe(false)
    expect(gradeLocally('', 'anything')).toBe(false)
  })
})

describe('offline pack storage', () => {
  it('round-trips a pack', () => {
    const pack = { exercises: [{ id: 1, prompt: 'p', answer: 'a' }] }
    expect(savePack(pack)).toBe(true)
    expect(loadPack()).toEqual(pack)
  })

  it('returns null when nothing is stored or data is corrupt', () => {
    expect(loadPack()).toBeNull()
    localStorage.setItem('offlinePack', '{not json')
    expect(loadPack()).toBeNull()
  })

  it('clears the pack', () => {
    savePack({ exercises: [] })
    clearPack()
    expect(loadPack()).toBeNull()
  })
})

describe('answer outbox', () => {
  it('queues answers with a unique id and timestamp', () => {
    const a = enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'habe', correct: true })
    const b = enqueueAnswer({ exerciseId: 2, userId: 5, answer: 'hast', correct: false })
    expect(queueSize()).toBe(2)
    expect(a.client_event_id).not.toBe(b.client_event_id)
    expect(a.answered_at).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    expect(getQueue()[0].exercise_id).toBe(1)
  })

  it('survives corrupt storage', () => {
    localStorage.setItem('offlineQueue', 'garbage')
    expect(getQueue()).toEqual([])
  })
})

describe('flashcard pack and queue', () => {
  it('round-trips a card pack independently of the exercise pack', () => {
    savePack({ exercises: [{ id: 1 }] })
    saveCardPack({ flashcards: [{ id: 9, word: 'Hund', translation: 'dog' }] })
    expect(loadCardPack().flashcards[0].word).toBe('Hund')
    expect(loadPack().exercises[0].id).toBe(1) // untouched
    clearCardPack()
    expect(loadCardPack()).toBeNull()
    expect(loadPack()).not.toBeNull()
  })

  it('queues a self-rated review with its rating and timestamp', () => {
    const e = enqueueFlashcardReview({ flashcardId: 9, userId: 5, rating: 3 })
    expect(e.kind).toBe(KIND_FLASHCARD)
    expect(e.rating).toBe(3)
    expect(e.reviewed_at).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    expect(getQueue()[0].flashcard_id).toBe(9)
  })

  it('counts pending events per kind in a shared outbox', () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    enqueueFlashcardReview({ flashcardId: 9, userId: 5, rating: 4 })
    enqueueFlashcardReview({ flashcardId: 10, userId: 5, rating: 1 })
    expect(queueSize()).toBe(3)
    expect(pendingByKind(KIND_EXERCISE)).toBe(1)
    expect(pendingByKind(KIND_FLASHCARD)).toBe(2)
  })
})

describe('lesson completion outbox', () => {
  it('queues a completion with an id and timestamp', () => {
    const e = enqueueLessonComplete({ lessonId: 42, userId: 5 })
    expect(e.kind).toBe(KIND_LESSON)
    expect(e.lesson_id).toBe(42)
    expect(e.completed_at).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    expect(getQueue()[0].client_event_id).toBe(e.client_event_id)
  })

  it('routes lesson completions to their handler on sync', async () => {
    enqueueLessonComplete({ lessonId: 42, userId: 5 })
    const lesson = vi.fn().mockResolvedValue({})
    const res = await syncQueue(handlers(vi.fn(), vi.fn(), lesson))
    expect(lesson).toHaveBeenCalledTimes(1)
    expect(lesson.mock.calls[0][0].lesson_id).toBe(42)
    expect(res).toEqual({ synced: 1, failed: 0 })
    expect(queueSize()).toBe(0)
  })
})

describe('syncQueue', () => {
  it('does nothing on an empty queue', async () => {
    const post = vi.fn()
    expect(await syncQueue(handlers(post))).toEqual({ synced: 0, failed: 0 })
    expect(post).not.toHaveBeenCalled()
  })

  it('routes each event to the handler for its kind', async () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    enqueueFlashcardReview({ flashcardId: 9, userId: 5, rating: 3 })
    const ex = vi.fn().mockResolvedValue({})
    const fc = vi.fn().mockResolvedValue({})

    const res = await syncQueue(handlers(ex, fc))

    expect(ex).toHaveBeenCalledTimes(1)
    expect(fc).toHaveBeenCalledTimes(1)
    expect(fc.mock.calls[0][0].flashcard_id).toBe(9)
    expect(res).toEqual({ synced: 2, failed: 0 })
    expect(queueSize()).toBe(0)
  })

  it('treats events without a kind as exercise answers (older builds)', async () => {
    localStorage.setItem('offlineQueue', JSON.stringify([
      { client_event_id: 'legacy-1', exercise_id: 3, user_id: 5, answer: 'a' },
    ]))
    const ex = vi.fn().mockResolvedValue({})
    await syncQueue(handlers(ex))
    expect(ex).toHaveBeenCalledTimes(1)
    expect(queueSize()).toBe(0)
  })

  it('keeps events queued when the network fails', async () => {
    enqueueFlashcardReview({ flashcardId: 9, userId: 5, rating: 3 })
    const fc = vi.fn().mockRejectedValue(new Error('offline'))

    const res = await syncQueue(handlers(vi.fn(), fc))

    expect(res).toEqual({ synced: 0, failed: 1 })
    expect(queueSize()).toBe(1) // retried on the next reconnect
  })

  it('reads the status from the API client error shape', async () => {
    // client.js rejects with a plain Error carrying .status (not an axios error),
    // so the queue must understand that shape too — otherwise a permanently
    // rejected event would be retried forever.
    enqueueFlashcardReview({ flashcardId: 999, userId: 5, rating: 3 })
    const err = Object.assign(new Error('Not found'), { status: 404 })
    const fc = vi.fn().mockRejectedValue(err)

    const res = await syncQueue(handlers(vi.fn(), fc))

    expect(res.failed).toBe(0)
    expect(queueSize()).toBe(0)
  })

  it('stops on 401 and keeps every remaining event', async () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    enqueueAnswer({ exerciseId: 2, userId: 5, answer: 'b', correct: true })
    enqueueAnswer({ exerciseId: 3, userId: 5, answer: 'c', correct: true })
    const ex = vi.fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(Object.assign(new Error('Locked'), { status: 401 }))

    const res = await syncQueue(handlers(ex))

    // First one went through; the failing one AND the untried one stay queued
    expect(res.synced).toBe(1)
    expect(queueSize()).toBe(2)
    expect(getQueue().map(e => e.exercise_id)).toEqual([2, 3])
  })

  it('drops events the server rejects permanently', async () => {
    enqueueFlashcardReview({ flashcardId: 999, userId: 5, rating: 3 })
    const fc = vi.fn().mockRejectedValue({ response: { status: 404 } })

    const res = await syncQueue(handlers(vi.fn(), fc))

    // A deleted card must not block the queue forever
    expect(res.failed).toBe(0)
    expect(queueSize()).toBe(0)
  })

  it('drops events of an unknown kind instead of blocking', async () => {
    localStorage.setItem('offlineQueue', JSON.stringify([{ kind: 'from_the_future' }]))
    const res = await syncQueue(handlers())
    expect(res).toEqual({ synced: 0, failed: 0 })
    expect(queueSize()).toBe(0)
  })

  it('retries only the failed events', async () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    enqueueAnswer({ exerciseId: 2, userId: 5, answer: 'b', correct: true })
    const ex = vi.fn()
      .mockResolvedValueOnce({ duplicate: false })
      .mockRejectedValueOnce(new Error('network'))

    const res = await syncQueue(handlers(ex))

    expect(res).toEqual({ synced: 1, failed: 1 })
    expect(getQueue()).toHaveLength(1)
    expect(getQueue()[0].exercise_id).toBe(2)
  })

  it('clears the queue on demand', () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    clearQueue()
    expect(queueSize()).toBe(0)
  })
})
