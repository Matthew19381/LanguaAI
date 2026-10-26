import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, Mic, MicOff, Volume2, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import {
  getUserId, startExam, getExam, getExamHistory, sendExamTeil1, finishExamTeil1,
  submitExamTeil2, submitExamTeil3, scoreExam, generateTTS,
} from '../api/client'
import { useDictation } from '../hooks/useDictation'

// Mock Goethe-Zertifikat B1 "Sprechen" (A5). Parts and points follow the
// Goethe Modellsatz; scoring is done by the backend (services/mock_exam.py).

const PART_NAMES = { teil1: 'Teil 1: wspólne planowanie', teil2: 'Teil 2: prezentacja', teil3: 'Teil 3: rozmowa o tematach' }
const CRITERIA = {
  erfuellung: 'Wykonanie zadania', interaktion: 'Interakcja', kohaerenz: 'Spójność',
  wortschatz: 'Słownictwo', strukturen: 'Gramatyka',
}

function fmt(s) {
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

function useSeconds(running, countdownFrom = null, resetKey = null) {
  const [s, setS] = useState(countdownFrom ?? 0)
  useEffect(() => {
    setS(countdownFrom ?? 0)
    if (!running) return
    const id = setInterval(() => setS(v => (countdownFrom != null ? Math.max(0, v - 1) : v + 1)), 1000)
    return () => clearInterval(id)
  }, [running, countdownFrom, resetKey])
  return s
}

async function speak(text) {
  try {
    const { url } = await generateTTS(text, 'German')
    if (url) new Audio(url).play()
  } catch (e) {
    console.error('TTS failed:', e)
  }
}

function MicButton({ dictation, testId }) {
  if (!dictation.supported) return null
  return (
    <button type="button" data-testid={testId} onClick={dictation.toggle}
      className={dictation.recording ? 'btn-danger flex items-center gap-2' : 'btn-secondary flex items-center gap-2'}>
      {dictation.recording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
      {dictation.recording ? 'Zatrzymaj nagrywanie' : 'Mów'}
    </button>
  )
}

function SpokenField({ value, onChange, placeholder, testId, rows = 4 }) {
  const dictation = useDictation(text => onChange(prev => (prev ? prev + ' ' : '') + text))
  return (
    <div className="space-y-2">
      <textarea data-testid={testId} rows={rows} value={value} placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        className="w-full rounded-lg bg-gray-800 border border-gray-700 p-3 text-gray-100" />
      <div className="flex items-center gap-3">
        <MicButton dictation={dictation} testId={`${testId}-mic`} />
        {dictation.error && <span className="text-red-400 text-sm">{dictation.error}</span>}
      </div>
    </div>
  )
}

function Results({ exam, history }) {
  const score = exam.score
  return (
    <div className="space-y-4" data-testid="exam-results">
      <div className="card">
        <div className="flex items-center gap-3">
          {score.passed ? <CheckCircle2 className="w-8 h-8 text-emerald-400" /> : <XCircle className="w-8 h-8 text-red-400" />}
          <div>
            <div className="text-2xl font-bold">{score.percent}%</div>
            <div className="text-gray-400 text-sm">
              {score.points} z {score.max_points} ocenianych punktów, próg 60%. {score.passed ? 'Zdany.' : 'Jeszcze nie.'}
            </div>
          </div>
        </div>
        <p className="text-gray-500 text-xs mt-3">
          Wymowa (16 z 100 punktów egzaminu) nie jest tu oceniana, bo ocena idzie z zapisu tekstu.
          Wynik to średnia dwóch niezależnych ocen, jak u dwóch egzaminatorów Goethe.
        </p>
      </div>
      {Object.entries(score.parts).map(([part, crits]) => (
        <div className="card" key={part}>
          <h3 className="font-semibold mb-2">{PART_NAMES[part]}</h3>
          <div className="space-y-3">
            {Object.entries(crits).map(([name, c]) => (
              <div key={name}>
                <div className="flex justify-between text-sm">
                  <span>{CRITERIA[name]}</span>
                  <span className="text-gray-400">{c.points}/{c.max} (poziom {c.levels.join(', ')})</span>
                </div>
                {c.reason && <p className="text-gray-400 text-sm">{c.reason}</p>}
                {c.errors?.length > 0 && (
                  <ul className="text-sm text-amber-300 list-disc ml-5">
                    {c.errors.map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
      {history && <Goal goal={history.goal} />}
    </div>
  )
}

function Goal({ goal }) {
  return (
    <p className="text-sm text-gray-300" data-testid="exam-goal">
      Cel „Mówienie B1”: {goal.reached
        ? 'osiągnięty (dwa ostatnie egzaminy co najmniej 60%).'
        : `jeszcze nie. Potrzebne są dwa kolejne egzaminy z wynikiem co najmniej 60%${goal.last_two.length ? `; ostatnie: ${goal.last_two.join('%, ')}%` : ''}.`}
    </p>
  )
}

export default function Exam() {
  const navigate = useNavigate()
  const userId = getUserId()
  const [history, setHistory] = useState(null)
  const [exam, setExam] = useState(null)
  const [prep, setPrep] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [topic, setTopic] = useState(0)
  const [transcript, setTranscript] = useState('')
  const [feedback, setFeedback] = useState('')
  const [answer, setAnswer] = useState('')
  const [showPartnerText, setShowPartnerText] = useState(false)
  const scoringStarted = useRef(false)

  const prepLeft = useSeconds(prep, exam ? exam.prep_minutes * 60 : 0)
  const partSeconds = useSeconds(Boolean(exam) && !prep && ['teil1', 'teil2'].includes(exam?.status), null, exam?.status)

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    getExamHistory(userId).then(setHistory).catch(e => setError(e.message))
  }, [userId])

  const run = async (fn) => {
    setBusy(true)
    setError('')
    try { return await fn() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const doScore = (examId) => run(async () => {
    const scored = await scoreExam(examId, userId)
    setExam(scored)
    setHistory(await getExamHistory(userId))
  })

  useEffect(() => {
    if (exam?.status === 'scoring' && !scoringStarted.current) {
      scoringStarted.current = true
      doScore(exam.exam_id)
    }
  }, [exam?.status])

  const begin = () => run(async () => {
    const e = await startExam(userId)
    scoringStarted.current = false
    setExam(e)
    setPrep(true)
  })

  const resume = () => run(async () => {
    const e = await getExam(history.unfinished_exam_id, userId)
    scoringStarted.current = false
    setExam(e)
    setPrep(e.status === 'teil1' && !e.teil1_history.some(m => m.role === 'user'))
  })

  const send = () => run(async () => {
    const text = message.trim()
    if (!text) return
    const r = await sendExamTeil1(exam.exam_id, userId, text)
    setMessage('')
    setExam(prev => ({ ...prev, teil1_history: [...prev.teil1_history, { role: 'user', content: text }, { role: 'assistant', content: r.reply }] }))
    speak(r.reply)
  })

  if (!exam) {
    return (
      <div className="page-container space-y-4">
        <h1 className="text-2xl font-bold flex items-center gap-2"><GraduationCap className="w-7 h-7 text-emerald-400" /> Próbny egzamin B1 „Sprechen”</h1>
        <div className="card space-y-2 text-sm text-gray-300">
          <p>Trzy części jak na egzaminie Goethe-Zertifikat B1: wspólne planowanie z partnerem (ok. 3 min), prezentacja tematu na 5 slajdach (ok. 3 min) i rozmowa o tematach (ok. 2 min). Najpierw 15 minut przygotowania.</p>
          <p>Mów do mikrofonu albo wpisuj. Na końcu dostajesz punkty według kryteriów Goethe.</p>
        </div>
        {history && <Goal goal={history.goal} />}
        <div className="flex gap-3">
          <button className="btn-primary" onClick={begin} disabled={busy} data-testid="exam-start">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Zacznij egzamin'}
          </button>
          {history?.unfinished_exam_id && (
            <button className="btn-secondary" onClick={resume} disabled={busy}>Dokończ rozpoczęty</button>
          )}
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}
        {history?.exams?.length > 0 && (
          <div className="card">
            <h3 className="font-semibold mb-2">Historia</h3>
            <ul className="text-sm space-y-1" data-testid="exam-history">
              {history.exams.map(e => (
                <li key={e.exam_id} className="flex justify-between">
                  <span>{e.scored_at?.slice(0, 10)}</span>
                  <span className={e.passed ? 'text-emerald-400' : 'text-gray-400'}>{e.percent}%</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  const { tasks } = exam
  return (
    <div className="page-container space-y-4">
      <h1 className="text-xl font-bold">Próbny egzamin B1 „Sprechen”</h1>
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {prep && (
        <div className="card space-y-3" data-testid="exam-prep">
          <div className="flex justify-between">
            <h2 className="font-semibold">Przygotowanie</h2>
            <span className="text-emerald-400 font-mono">{fmt(prepLeft)}</span>
          </div>
          <p className="text-sm text-gray-300"><b>Teil 1:</b> {tasks.teil1.situation}</p>
          <ul className="text-sm list-disc ml-5">{tasks.teil1.points.map(p => <li key={p}>{p}</li>)}</ul>
          <p className="text-sm text-gray-300"><b>Teil 2:</b> wybierz temat i przygotuj notatki do 5 slajdów.</p>
          {tasks.teil2.topics.map((tp, i) => (
            <label key={i} className="flex gap-2 text-sm">
              <input type="radio" checked={topic === i} onChange={() => setTopic(i)} /> {tp.title}
            </label>
          ))}
          <ol className="text-xs text-gray-400 list-decimal ml-5">{exam.slides.map(s => <li key={s}>{s}</li>)}</ol>
          <button className="btn-primary" onClick={() => setPrep(false)} data-testid="exam-prep-done">Zaczynam</button>
        </div>
      )}

      {!prep && exam.status === 'teil1' && (
        <div className="card space-y-3" data-testid="exam-teil1">
          <div className="flex justify-between">
            <h2 className="font-semibold">{PART_NAMES.teil1}</h2>
            <span className="font-mono text-gray-400">{fmt(partSeconds)} / ok. 3:00</span>
          </div>
          <p className="text-sm text-gray-300">{tasks.teil1.situation}</p>
          <ul className="text-sm list-disc ml-5 text-gray-400">{tasks.teil1.points.map(p => <li key={p}>{p}</li>)}</ul>
          <div className="space-y-2">
            {exam.teil1_history.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
                <span className={`inline-block rounded-lg px-3 py-2 text-sm ${m.role === 'user' ? 'bg-emerald-800' : 'bg-gray-800'}`}>
                  {m.content}
                  {m.role === 'assistant' && (
                    <button className="ml-2 align-middle" onClick={() => speak(m.content)} aria-label="Odsłuchaj"><Volume2 className="w-4 h-4 inline" /></button>
                  )}
                </span>
              </div>
            ))}
          </div>
          <SpokenField value={message} onChange={setMessage} rows={2} testId="exam-teil1-input" placeholder="Twoja wypowiedź po niemiecku" />
          <div className="flex gap-3">
            <button className="btn-primary" onClick={send} disabled={busy || !message.trim()} data-testid="exam-teil1-send">Wyślij</button>
            <button className="btn-secondary" disabled={busy}
              onClick={() => run(async () => setExam(await finishExamTeil1(exam.exam_id, userId)))}
              data-testid="exam-teil1-finish">Koniec części 1</button>
          </div>
        </div>
      )}

      {!prep && exam.status === 'teil2' && (
        <div className="card space-y-3" data-testid="exam-teil2">
          <div className="flex justify-between">
            <h2 className="font-semibold">{PART_NAMES.teil2}</h2>
            <span className="font-mono text-gray-400">{fmt(partSeconds)} / ok. 3:00</span>
          </div>
          {tasks.teil2.topics.map((tp, i) => (
            <label key={i} className="flex gap-2 text-sm">
              <input type="radio" checked={topic === i} onChange={() => setTopic(i)} /> {tp.title}
            </label>
          ))}
          <ol className="text-sm text-gray-300 list-decimal ml-5">{exam.slides.map(s => <li key={s}>{s}</li>)}</ol>
          <p className="text-xs text-gray-500">Włącz „Mów” i mów całą prezentację. Tekst możesz poprawić tam, gdzie rozpoznawanie mowy się pomyliło, ale nie dopisuj nowych treści.</p>
          <SpokenField value={transcript} onChange={setTranscript} rows={8} testId="exam-teil2-input" placeholder="Twoja prezentacja" />
          <button className="btn-primary" disabled={busy}
            onClick={() => run(async () => setExam(await submitExamTeil2(exam.exam_id, userId, topic, transcript)))}
            data-testid="exam-teil2-submit">Koniec prezentacji</button>
        </div>
      )}

      {exam.status === 'teil3' && (
        <div className="card space-y-3" data-testid="exam-teil3">
          <h2 className="font-semibold">{PART_NAMES.teil3}</h2>
          <div className="space-y-2">
            <p className="text-sm text-gray-300">Partner pyta o Twoją prezentację:</p>
            <p className="bg-gray-800 rounded-lg px-3 py-2 text-sm" data-testid="exam-teil3-question">
              {exam.teil3.question}
              <button className="ml-2" onClick={() => speak(exam.teil3.question)} aria-label="Odsłuchaj"><Volume2 className="w-4 h-4 inline" /></button>
            </p>
            <SpokenField value={answer} onChange={setAnswer} rows={3} testId="exam-teil3-answer" placeholder="Twoja odpowiedź" />
          </div>
          <div className="space-y-2">
            <p className="text-sm text-gray-300">Prezentacja partnera: „{tasks.teil3.partner_presentation.title}”. Wysłuchaj jej, potem powiedz krótko, co o niej sądzisz, i zadaj jedno pytanie.</p>
            <div className="flex gap-3">
              <button className="btn-secondary flex items-center gap-2" onClick={() => speak(tasks.teil3.partner_presentation.text)}>
                <Volume2 className="w-4 h-4" /> Odsłuchaj
              </button>
              <button className="btn-secondary" onClick={() => setShowPartnerText(v => !v)}>{showPartnerText ? 'Ukryj tekst' : 'Pokaż tekst'}</button>
            </div>
            {showPartnerText && <p className="text-sm text-gray-400">{tasks.teil3.partner_presentation.text}</p>}
            <SpokenField value={feedback} onChange={setFeedback} rows={3} testId="exam-teil3-feedback" placeholder="Twoja reakcja i pytanie" />
          </div>
          <button className="btn-primary" disabled={busy}
            onClick={() => run(async () => setExam(await submitExamTeil3(exam.exam_id, userId, answer, feedback)))}
            data-testid="exam-teil3-submit">Zakończ egzamin</button>
        </div>
      )}

      {exam.status === 'scoring' && (
        <div className="card space-y-2" data-testid="exam-scoring">
          {busy
            ? <p className="flex items-center gap-2 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Oceniam według kryteriów Goethe…</p>
            : <button className="btn-primary" onClick={() => doScore(exam.exam_id)}>Oceń ponownie</button>}
        </div>
      )}

      {exam.status === 'scored' && <Results exam={exam} history={history} />}
    </div>
  )
}
