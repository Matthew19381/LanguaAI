import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Mic, MicOff, Timer, MessageSquare, GraduationCap, FlaskConical, Layers } from 'lucide-react'
import { useDictation } from '../hooks/useDictation'

// A3: what each day type of the A2→B1 programme asks for, with the screen
// that does it. Day types and their rhythm: services/curriculum.py.

const ROUNDS = [90, 60, 45]  // 4/3/2 scaled to the programme's 90/60/45 s

function FluencyDrill({ task }) {
  const [round, setRound] = useState(0)          // index into ROUNDS
  const [left, setLeft] = useState(null)         // seconds left in the running round
  const [words, setWords] = useState([])         // words spoken per finished round
  const [counting, setCounting] = useState(false)
  const current = useRef([])
  const dictation = useDictation(text => { current.current.push(text) })

  useEffect(() => {
    if (left === null) return
    if (left === 0) {
      dictation.stop()
      setLeft(null)
      setCounting(true)
      return
    }
    const id = setTimeout(() => setLeft(l => l - 1), 1000)
    return () => clearTimeout(id)
  }, [left])

  // The last phrase is recognised only after the mic stops, so count a moment later.
  useEffect(() => {
    if (!counting) return
    const id = setTimeout(() => {
      const count = current.current.join(' ').split(/\s+/).filter(Boolean).length
      setWords(w => [...w, count])
      setRound(r => r + 1)
      setCounting(false)
    }, 1500)
    return () => clearTimeout(id)
  }, [counting])

  const start = () => {
    current.current = []
    setLeft(ROUNDS[round])
    if (dictation.supported) dictation.start()
  }

  return (
    <div className="space-y-2" data-testid="fluency-drill">
      <p className="text-sm text-gray-300">Opowiedz to samo zadanie 3 razy, za każdym razem w krótszym czasie: 90, 60 i 45 sekund. Tylko słowa, które znasz; nie zatrzymuj się na błędach.</p>
      {task && <p className="text-sm font-medium text-indigo-300">{task}</p>}
      <div className="flex flex-wrap items-center gap-3">
        {round < ROUNDS.length && left === null && !counting && (
          <button className="btn-primary flex items-center gap-2" onClick={start} data-testid="fluency-start">
            <Timer className="w-4 h-4" /> Runda {round + 1}: {ROUNDS[round]} s
          </button>
        )}
        {left !== null && (
          <span className="font-mono text-2xl text-emerald-400" data-testid="fluency-left">{left} s</span>
        )}
        {left !== null && dictation.recording && <Mic className="w-5 h-5 text-red-400" />}
        {left !== null && !dictation.recording && dictation.supported && <MicOff className="w-5 h-5 text-gray-500" />}
      </div>
      {words.length > 0 && (
        <ul className="text-sm text-gray-400" data-testid="fluency-results">
          {words.map((w, i) => (
            <li key={i}>Runda {i + 1}: {w} słów, {Math.round(w * 60 / ROUNDS[i])} słów na minutę</li>
          ))}
        </ul>
      )}
      {!dictation.supported && <p className="text-xs text-gray-500">Ta przeglądarka nie rozpoznaje mowy, więc licznik słów nie działa; sam stoper działa.</p>}
      {dictation.error && <p className="text-xs text-red-400">{dictation.error}</p>}
      <p className="text-xs text-gray-500">Podstawa: powtarzanie tego samego monologu pod presją czasu (4/3/2); płynność utrzymała się przy tym samym temacie (De Jong i Perfetti 2011).</p>
    </div>
  )
}

export default function DayTypeCard({ dayType, moduleId, moduleTask }) {
  if (!dayType) return null
  const body = {
    nowy_material: {
      title: 'Nowy materiał',
      text: 'Dziś gramatyka i słowa tego modułu, tekst do słuchania i czytania, na końcu krótko mówisz.',
    },
    zadanie_mowione: {
      title: 'Zadanie mówione',
      text: 'Po lekcji przećwicz zadanie modułu na głos w rozmowie. Rozmówca daje podpowiedź przy błędzie, zanim poda poprawną formę.',
      action: <Link to="/conversation" className="btn-primary inline-flex items-center gap-2" data-testid="daytype-action"><MessageSquare className="w-4 h-4" /> Ćwicz zadanie modułu</Link>,
    },
    plynnosc: {
      title: 'Płynność',
      text: 'Dziś bez nowej gramatyki. Mówisz to samo zadanie coraz szybciej.',
      extra: <FluencyDrill task={moduleTask} />,
    },
    test_bledy: {
      title: 'Test i własne błędy',
      text: 'Krótki test umiejętności z tego tygodnia i powtórka Twoich ostatnich błędów.',
      action: (
        <div className="flex flex-wrap gap-2">
          <Link to="/test" className="btn-primary inline-flex items-center gap-2" data-testid="daytype-action"><FlaskConical className="w-4 h-4" /> Test</Link>
          <Link to="/errors" className="btn-secondary inline-flex items-center gap-2">Moje błędy</Link>
        </div>
      ),
    },
    probny_egzamin: {
      title: 'Próbny egzamin ustny',
      text: 'Dziś próbny egzamin B1 „Sprechen” (3 części, ok. 15 minut po 15 minutach przygotowania). Potem wróć tutaj i zakończ lekcję, żeby dzień odhaczył się w planie.',
      action: <Link to="/exam" className="btn-primary inline-flex items-center gap-2" data-testid="daytype-action"><GraduationCap className="w-4 h-4" /> Egzamin</Link>,
    },
    naprawa: {
      title: 'Powtórka naprawcza',
      text: 'Umiejętności z poprzedniego modułu nie są jeszcze opanowane. Dziś bez nowej gramatyki: te same reguły inaczej wyjaśnione, przykłady z Twoich błędów i znów zadanie modułu.',
      action: <Link to="/topics" className="btn-secondary inline-flex items-center gap-2" data-testid="daytype-action"><Layers className="w-4 h-4" /> Bank wiedzy</Link>,
    },
  }[dayType]
  if (!body) return null
  return (
    <div className="card mb-6 space-y-3" data-testid="day-type-card">
      <div className="flex items-center gap-2">
        <span className="badge-blue">{moduleId}</span>
        <h2 className="font-semibold">Typ dnia: {body.title}</h2>
      </div>
      <p className="text-sm text-gray-300">{body.text}</p>
      {moduleTask && dayType !== 'plynnosc' && <p className="text-xs text-gray-500">Zadanie modułu: {moduleTask}</p>}
      {body.extra}
      {body.action}
    </div>
  )
}
