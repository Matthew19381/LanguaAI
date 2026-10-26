import { useEffect, useRef, useState } from 'react'

// Continuous Web Speech dictation for long answers (mock exam presentation).
// Browsers end a recognition session on their own after a pause, so while the
// user keeps recording it is restarted; only final results are passed on.
export function useDictation(onText, lang = 'de-DE') {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const recRef = useRef(null)
  const wantRef = useRef(false)
  const onTextRef = useRef(onText)
  onTextRef.current = onText

  const supported = typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)

  const stop = () => {
    wantRef.current = false
    recRef.current?.stop()
    setRecording(false)
  }

  const start = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { setError('Ta przeglądarka nie rozpoznaje mowy. Wpisz tekst.'); return }
    const rec = new SR()
    rec.lang = lang
    rec.continuous = true
    rec.interimResults = false
    rec.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) onTextRef.current(event.results[i][0].transcript.trim())
      }
    }
    rec.onerror = (event) => {
      if (event.error === 'no-speech') return
      setError('Błąd rozpoznawania mowy: ' + event.error)
      wantRef.current = false
    }
    rec.onend = () => {
      if (wantRef.current) {
        try { rec.start(); return } catch { /* fall through to stopped */ }
      }
      setRecording(false)
    }
    try {
      wantRef.current = true
      rec.start()
      recRef.current = rec
      setRecording(true)
      setError('')
    } catch (e) {
      wantRef.current = false
      setError('Nie udało się włączyć mikrofonu: ' + e.message)
    }
  }

  useEffect(() => () => { wantRef.current = false; recRef.current?.stop() }, [])

  return { recording, error, supported, start, stop, toggle: () => (recording ? stop() : start()) }
}
