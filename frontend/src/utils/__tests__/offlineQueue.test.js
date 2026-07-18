import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  gradeLocally, normalizeAnswer, savePack, loadPack, clearPack,
  enqueueAnswer, getQueue, queueSize, clearQueue, syncQueue,
} from '../offlineQueue'

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

describe('syncQueue', () => {
  it('does nothing on an empty queue', async () => {
    const post = vi.fn()
    expect(await syncQueue(post)).toEqual({ synced: 0, failed: 0 })
    expect(post).not.toHaveBeenCalled()
  })

  it('sends every queued answer and empties the queue', async () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    enqueueAnswer({ exerciseId: 2, userId: 5, answer: 'b', correct: false })
    const post = vi.fn().mockResolvedValue({ duplicate: false })

    const res = await syncQueue(post)

    expect(post).toHaveBeenCalledTimes(2)
    expect(res).toEqual({ synced: 2, failed: 0 })
    expect(queueSize()).toBe(0)
  })

  it('keeps answers queued when the network fails', async () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    const post = vi.fn().mockRejectedValue(new Error('offline'))

    const res = await syncQueue(post)

    expect(res).toEqual({ synced: 0, failed: 1 })
    expect(queueSize()).toBe(1) // retried on the next reconnect
  })

  it('drops answers the server rejects permanently', async () => {
    enqueueAnswer({ exerciseId: 999, userId: 5, answer: 'a', correct: true })
    const post = vi.fn().mockRejectedValue({ response: { status: 404 } })

    const res = await syncQueue(post)

    // A deleted exercise must not block the queue forever
    expect(res.failed).toBe(0)
    expect(queueSize()).toBe(0)
  })

  it('retries only the failed answers', async () => {
    enqueueAnswer({ exerciseId: 1, userId: 5, answer: 'a', correct: true })
    enqueueAnswer({ exerciseId: 2, userId: 5, answer: 'b', correct: true })
    const post = vi.fn()
      .mockResolvedValueOnce({ duplicate: false })
      .mockRejectedValueOnce(new Error('network'))

    const res = await syncQueue(post)

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
