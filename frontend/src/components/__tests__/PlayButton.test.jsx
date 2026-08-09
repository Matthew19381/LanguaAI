import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PlayButton from '../PlayButton'

// jsdom has no real audio pipeline — stub the parts PlayButton touches, and
// keep a registry so tests can reach the instance the component created.
let instances = []
class FakeAudio {
  constructor(url) {
    this.url = url
    this.currentTime = 0
    this.onended = null
    this.onerror = null
    this.paused = false
    instances.push(this)
  }
  play() { this.paused = false }
  pause() { this.paused = true }
}

describe('PlayButton', () => {
  beforeEach(() => {
    instances = []
    vi.stubGlobal('Audio', FakeAudio)
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ url: '/audio/test.mp3' }),
      })
    ))
  })

  it('fetches TTS and starts playing on click', async () => {
    render(<PlayButton text="Hallo" language="German" />)
    const button = screen.getByRole('button')
    fireEvent.click(button)

    await waitFor(() => {
      expect(button).toHaveAttribute('title', 'Zatrzymaj')
    })
    expect(fetch).toHaveBeenCalledWith('/api/audio/tts', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ text: 'Hallo', language: 'German' }),
    }))
    expect(instances).toHaveLength(1)
    expect(instances[0].paused).toBe(false)
  })

  it('stops playback on a second click instead of restarting', async () => {
    render(<PlayButton text="Hallo" language="German" />)
    const button = screen.getByRole('button')
    fireEvent.click(button)
    await waitFor(() => expect(button).toHaveAttribute('title', 'Zatrzymaj'))

    fireEvent.click(button)
    // Back to the "play" state — a second click stops, it doesn't re-fetch.
    expect(button).toHaveAttribute('title', 'Play: Hallo')
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(instances[0].paused).toBe(true)
  })

  it('returns to the play state on its own when playback ends', async () => {
    render(<PlayButton text="Hallo" language="German" />)
    const button = screen.getByRole('button')
    fireEvent.click(button)
    await waitFor(() => expect(button).toHaveAttribute('title', 'Zatrzymaj'))

    // Simulate the audio element reaching its natural end.
    instances[0].onended()

    await waitFor(() => {
      expect(button).toHaveAttribute('title', 'Play: Hallo')
    })
  })

  it('does not fetch when text is empty', () => {
    render(<PlayButton text="" language="German" />)
    fireEvent.click(screen.getByRole('button'))
    expect(fetch).not.toHaveBeenCalled()
  })
})
