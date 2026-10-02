// Text-to-speech playback shared by PlayButton (manual) and flashcard auto-play.

export async function fetchTtsUrl(text, language) {
  const res = await fetch('/api/audio/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language: language || 'German' }),
  })
  if (!res.ok) throw new Error('TTS failed')
  const data = await res.json()
  if (!data?.url) throw new Error('No audio URL in response')
  return data.url
}

// Plays `texts` one after another. Best-effort: a failed TTS call (offline)
// or a play() the browser blocks (no user gesture yet on this page) just skips
// that text. Returns a cancel function that stops playback immediately.
export function playSequence(texts, language) {
  let cancelled = false
  let audio = null
  let finishCurrent = null

  ;(async () => {
    for (const text of texts) {
      if (cancelled) return
      try {
        const url = await fetchTtsUrl(text, language)
        if (cancelled) return
        audio = new Audio(url)
        await new Promise((resolve) => {
          finishCurrent = resolve
          audio.onended = resolve
          audio.onerror = resolve
          Promise.resolve(audio.play()).catch(resolve)
        })
      } catch { /* best-effort */ }
    }
  })()

  return () => {
    cancelled = true
    audio?.pause()
    finishCurrent?.()
  }
}
