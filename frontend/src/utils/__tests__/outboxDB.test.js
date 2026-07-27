import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'
import { mirrorPut, mirrorGetAll, mirrorDelete } from '../outboxDB'

// fake-indexeddb gives us a real IndexedDB implementation in the test runner,
// so these exercise the actual mirror the service worker reads from.

async function reset() {
  for (const e of await mirrorGetAll()) await mirrorDelete(e.client_event_id)
}

describe('outbox IndexedDB mirror', () => {
  beforeEach(reset)

  it('stores and reads back a queued event', async () => {
    await mirrorPut({ client_event_id: 'a1', kind: 'exercise_answer', answer: 'habe' })
    const all = await mirrorGetAll()
    expect(all).toHaveLength(1)
    expect(all[0]).toMatchObject({ client_event_id: 'a1', answer: 'habe' })
  })

  it('is keyed by client_event_id (re-put updates, not duplicates)', async () => {
    await mirrorPut({ client_event_id: 'a1', rating: 1 })
    await mirrorPut({ client_event_id: 'a1', rating: 4 })
    const all = await mirrorGetAll()
    expect(all).toHaveLength(1)
    expect(all[0].rating).toBe(4)
  })

  it('deletes a replayed event', async () => {
    await mirrorPut({ client_event_id: 'a1' })
    await mirrorPut({ client_event_id: 'a2' })
    await mirrorDelete('a1')
    const ids = (await mirrorGetAll()).map(e => e.client_event_id)
    expect(ids).toEqual(['a2'])
  })

  it('ignores an event with no client_event_id', async () => {
    await mirrorPut({ kind: 'exercise_answer' })
    expect(await mirrorGetAll()).toHaveLength(0)
  })
})
