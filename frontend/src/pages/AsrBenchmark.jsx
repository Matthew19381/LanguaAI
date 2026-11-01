import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Mic, Square, Gauge, RotateCcw } from 'lucide-react'
import { getAsrSentences, uploadAsrRecording, evaluateAsr, getLatestAsr } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useDictation } from '../hooks/useDictation'

// A6: how well speech recognition understands the learner's own voice.
// Each sentence is recorded once; the browser's recogniser (the same settings
// as the mock exam) listens at the same time. The PC then runs the Whisper
// sizes on the recordings and compares word error rates.
const STORE_KEY = 'asr_benchmark_session'
const FINAL_WAIT_MS = 1500 // the recogniser delivers its last result after stop

const newSessionId = () =>
  (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`)

const loadSession = () => {
  try {
    const s = JSON.parse(localStorage.getItem(STORE_KEY) || 'null')
    if (s?.id && Array.isArray(s.done)) return s
  } catch { /* storage blocked: start a new session */ }
  return { id: newSessionId(), done: [] }
}

const saveSession = (s) => {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(s)) } catch { /* not critical */ }
}

const label = (name) => (name === 'browser'
  ? 'Przeglądarka (egzamin, rozmowa, ćwiczenie płynności)'
  : `Whisper ${name} (trener wymowy)`)

export default function AsrBenchmark() {
  const [sentences, setSentences] = useState([])
  const [currentWhisper, setCurrentWhisper] = useState('')
  const [session, setSession] = useState(loadSession)
  const [index, setIndex] = useState(0)
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const heardRef = useRef([])
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const initialDone = useRef(session.done)
  const dictation = useDictation((text) => heardRef.current.push(text))

  useEffect(() => {
    Promise.all([getAsrSentences(), getLatestAsr().catch(() => null)])
      .then(([s, latest]) => {
        setSentences(s.sentences || [])
        setCurrentWhisper(s.current_whisper || '')
        if (latest?.result) setResult(latest.result)
        const first = (s.sentences || []).findIndex((_, i) => !initialDone.current.includes(i))
        setIndex(first === -1 ? 0 : first)
      })
      .catch(() => setError('Nie udało się pobrać zdań z serwera.'))
      .finally(() => setLoading(false))
  }, [])

  // Leaving the page while recording kept the microphone on (01.11.2026)
  useEffect(() => () => {
    streamRef.current?.getTracks().forEach(t => t.stop())  // useDictation stops itself
  }, [])

  const start = async () => {
    setError('')
    heardRef.current = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream)
      const chunks = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
      recorder.stopped = new Promise((resolve) => {
        recorder.onstop = () => {
          stream.getTracks().forEach(t => t.stop())
          resolve(new Blob(chunks, { type: 'audio/webm' }))
        }
      })
      recorder.start()
      recorderRef.current = recorder
      if (dictation.supported) dictation.start()
      setRecording(true)
    } catch (e) {
      streamRef.current?.getTracks().forEach(t => t.stop())
      setError('Brak dostępu do mikrofonu: ' + e.message)
    }
  }

  const stop = async () => {
    const recorder = recorderRef.current
    if (!recorder) return
    setRecording(false)
    setBusy('upload')
    recorder.stop()
    const blob = await recorder.stopped
    await new Promise(r => setTimeout(r, FINAL_WAIT_MS))
    if (dictation.supported) dictation.stop()
    const form = new FormData()
    form.append('audio', blob, 'recording.webm')
    form.append('session_id', session.id)
    form.append('index', String(index))
    // null = the browser has no recogniser (not counted); '' = it heard nothing (100 % errors)
    if (dictation.supported) form.append('browser_text', heardRef.current.join(' '))
    try {
      await uploadAsrRecording(form)
      const next = { ...session, done: [...new Set([...session.done, index])] }
      setSession(next)
      saveSession(next)
      const following = sentences.findIndex((_, i) => !next.done.includes(i))
      if (following !== -1) setIndex(following)
    } catch (e) {
      setError('Nagranie nie zostało zapisane: ' + (e.response?.data?.detail || e.message))
    } finally {
      setBusy('')
    }
  }

  const evaluate = async () => {
    setError('')
    setBusy('evaluate')
    try {
      setResult(await evaluateAsr(session.id))
    } catch (e) {
      setError('Liczenie wyników nie powiodło się: ' + (e.response?.data?.detail || e.message))
    } finally {
      setBusy('')
    }
  }

  const restart = () => {
    const fresh = { id: newSessionId(), done: [] }
    setSession(fresh)
    saveSession(fresh)
    setIndex(0)
  }

  if (loading) return <PageLoader />

  const doneCount = session.done.length
  const allDone = sentences.length > 0 && doneCount >= sentences.length

  return (
    <div className="page-container max-w-xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <Gauge className="w-7 h-7 text-purple-400" />
        <div>
          <h1 className="text-2xl font-bold">Pomiar rozpoznawania mowy</h1>
          <p className="text-gray-400 text-sm">Jak dobrze aplikacja rozumie Twój niemiecki</p>
        </div>
      </div>

      <div className="card mb-4 text-sm text-gray-300 space-y-2">
        <p>Przeczytaj na głos {sentences.length} zdań, każde raz, normalnym tempem, w miejscu, w którym zwykle się uczysz.
          Nagrania zostają na komputerze (folder <code>backend/asr_pomiar</code>) i nie trafiają do repozytorium.</p>
        <p>Wynik to odsetek błędnie rozpoznanych słów (WER): im mniej, tym lepiej.</p>
        {!dictation.supported && (
          <p className="text-amber-300">Ta przeglądarka nie rozpoznaje mowy, więc zmierzony zostanie tylko Whisper.
            Egzamin i rozmowę mierzy się w Chrome.</p>
        )}
      </div>

      {sentences.length > 0 && (
        <div className="card mb-4" data-testid="asr-sentence-card">
          <div className="flex justify-between text-xs text-gray-500 mb-2">
            <span>Zdanie {index + 1} z {sentences.length}</span>
            <span data-testid="asr-progress">Nagrane: {doneCount} / {sentences.length}</span>
          </div>
          <p className="text-xl font-medium mb-4" data-testid="asr-sentence">{sentences[index]}</p>
          {session.done.includes(index) && !recording && (
            <p className="text-xs text-gray-500 mb-2">To zdanie jest już nagrane; nowe nagranie zastąpi poprzednie.</p>
          )}
          {!recording ? (
            <button className="btn-primary w-full flex items-center justify-center gap-2 py-4"
              onClick={start} disabled={Boolean(busy)} data-testid="asr-record">
              <Mic className="w-5 h-5" /> {busy === 'upload' ? 'Zapisywanie…' : 'Nagraj'}
            </button>
          ) : (
            <button className="w-full flex items-center justify-center gap-2 py-4 rounded-lg bg-red-600 text-white font-medium"
              onClick={stop} data-testid="asr-stop">
              <Square className="w-5 h-5" /> Stop
            </button>
          )}
          <div className="flex gap-2 mt-3">
            <button className="btn-secondary flex-1" disabled={recording || index === 0}
              onClick={() => setIndex(index - 1)}>Poprzednie</button>
            <button className="btn-secondary flex-1" disabled={recording || index >= sentences.length - 1}
              onClick={() => setIndex(index + 1)}>Następne</button>
          </div>
        </div>
      )}

      {(error || dictation.error) && <p className="text-red-400 text-sm mb-4">{error || dictation.error}</p>}

      <div className="card mb-4">
        <button className="btn-primary w-full" onClick={evaluate}
          disabled={doneCount === 0 || recording || Boolean(busy)} data-testid="asr-evaluate">
          {busy === 'evaluate' ? 'Liczenie… (na komputerze, może potrwać kilka minut)' : 'Policz wyniki'}
        </button>
        {!allDone && doneCount > 0 && (
          <p className="text-xs text-gray-500 mt-2">Wynik z mniej niż {sentences.length} zdań jest mniej pewny.</p>
        )}
        <button className="text-xs text-gray-500 mt-3 flex items-center gap-1" onClick={restart} disabled={recording || Boolean(busy)}>
          <RotateCcw className="w-3 h-3" /> Zacznij nową serię nagrań
        </button>
      </div>

      {result && (
        <div className="card mb-4" data-testid="asr-result">
          <h2 className="font-semibold mb-1">Wynik</h2>
          <p className="text-xs text-gray-500 mb-3">
            {new Date(result.measured_at).toLocaleString('pl-PL')}, nagrań: {result.recordings}
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 text-xs">
                <th className="pb-2">Rozpoznawanie</th><th className="pb-2">WER</th><th className="pb-2">s / zdanie</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.results).map(([name, r]) => (
                <tr key={name} className="border-t border-gray-800" data-testid={`asr-row-${name}`}>
                  <td className="py-2 pr-2">{label(name)}</td>
                  <td className="py-2 whitespace-nowrap">{r.wer == null ? (r.error ? 'błąd' : '–') : `${r.wer} %`}</td>
                  <td className="py-2">{r.avg_seconds == null ? '–' : r.avg_seconds}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {Object.entries(result.results).filter(([, r]) => r.error).map(([name, r]) => (
            <p key={name} className="text-xs text-red-400 mt-2">Whisper {name}: {r.error}</p>
          ))}
          {result.recommended_whisper ? (
            <p className="text-sm mt-3" data-testid="asr-recommendation">
              Zalecany model trenera wymowy: <b>{result.recommended_whisper}</b>
              {currentWhisper && ` (teraz: ${currentWhisper})`}. Zasada: {result.rule}.
              {currentWhisper && currentWhisper !== result.recommended_whisper && (
                <> Zmiana: w pliku <code>.env</code> w głównym folderze LinguaAI (tam, gdzie klucze API) wpisz <code>WHISPER_MODEL={result.recommended_whisper}</code> i uruchom backend ponownie.</>
              )}
            </p>
          ) : (
            <p className="text-sm mt-3 text-amber-300">Żaden model Whisper nie zadziałał, więc nie ma zalecenia.</p>
          )}
        </div>
      )}

      <Link to="/pronunciation" className="text-sm text-purple-400">← Trener wymowy</Link>
    </div>
  )
}
