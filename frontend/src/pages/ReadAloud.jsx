import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Volume2, ArrowRight, Check, Loader2, Mic } from 'lucide-react'
import { getUserId, getReadAloud } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'

/**
 * SCI-7 (production effect, MacLeod et al. 2010, RCT): words spoken aloud are
 * remembered better than words read silently. v1: no speech recognition —
 * the learner hears TTS, repeats aloud, and self-marks each word.
 */
export default function ReadAloud() {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [done, setDone] = useState({})
  const audioRef = useRef(null)
  const navigate = useNavigate()
  const userId = getUserId()
  const { t } = useLanguage()

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    getReadAloud(userId, 8)
      .then(data => setItems(data.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [userId])

  const current = items && items[index]
  const total = items ? items.length : 0
  const doneCount = Object.keys(done).length

  const play = () => {
    if (!current?.audio_path) return
    if (!audioRef.current) audioRef.current = new Audio(current.audio_path)
    else audioRef.current.src = current.audio_path
    audioRef.current.play().catch(() => {})
  }

  const markAndNext = () => {
    setDone(prev => ({ ...prev, [current.flashcard_id]: true }))
    setRevealed(false)
    if (index + 1 < total) setIndex(index + 1)
  }

  if (loading) return <PageLoader text="Przygotowuję słowa do powtórki na głos…" />

  if (!items || items.length === 0) {
    return (
      <div className="max-w-xl mx-auto p-6 text-center space-y-4">
        <Volume2 className="w-12 h-12 mx-auto text-blue-500" />
        <h1 className="text-xl font-bold dark:text-white">Powtórz na głos</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Nie masz jeszcze fiszek do powtarzania. Najpierw wygeneruj lekcję —
          nowe słowa trafią tutaj automatycznie.
        </p>
        <button onClick={() => navigate('/lesson')} className="px-4 py-2 rounded-lg bg-blue-600 text-white">
          Idź do lekcji
        </button>
      </div>
    )
  }

  if (doneCount >= total) {
    return (
      <div className="max-w-xl mx-auto p-6 text-center space-y-4">
        <Check className="w-12 h-12 mx-auto text-green-500" />
        <h1 className="text-xl font-bold dark:text-white">Świetna robota!</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Powtórzyłeś na głos {total} słów. Mówienie na głos wzmacnia zapamiętywanie
          (production effect) — wróć jutro po nową porcję.
        </p>
        <button onClick={() => navigate('/quickmode')} className="px-4 py-2 rounded-lg bg-blue-600 text-white">
          Wróć do Quick Mode
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto p-4 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold dark:text-white flex items-center gap-2">
          <Mic className="w-5 h-5 text-blue-500" /> Powtórz na głos
        </h1>
        <span className="text-sm text-gray-500 dark:text-gray-400">{doneCount}/{total}</span>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-300">
        Posłuchaj słowa, <strong>powiedz je głośno</strong>, potem odkryj tłumaczenie i oceń się sam.
      </p>

      <div className="rounded-2xl border dark:border-gray-700 bg-white dark:bg-gray-900 p-8 space-y-6 text-center">
        {current.lapsed && (
          <span className="inline-block px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 text-xs font-medium">
            Ostatnio Ci to nie poszło — spróbuj innym sposobem: na głos
          </span>
        )}
        <button
          onClick={play}
          disabled={!current?.audio_path}
          className="mx-auto w-16 h-16 rounded-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 flex items-center justify-center text-white"
          title="Odtwórz"
        >
          <Volume2 className="w-8 h-8" />
        </button>

        {!revealed ? (
          <button
            onClick={() => setRevealed(true)}
            className="px-6 py-3 rounded-lg border dark:border-gray-600 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Powiedziałem na głos — pokaż słowo
          </button>
        ) : (
          <div className="space-y-3">
            <div className="text-3xl font-bold dark:text-white">{current.word}</div>
            <div className="text-lg text-gray-600 dark:text-gray-300">{current.translation}</div>
            {current.example_sentence && (
              <div className="text-sm italic text-gray-500 dark:text-gray-400">{current.example_sentence}</div>
            )}
            <button
              onClick={markAndNext}
              className="mt-2 px-6 py-3 rounded-lg bg-green-600 hover:bg-green-700 text-white flex items-center gap-2 mx-auto"
            >
              {index + 1 < total ? <>Następne <ArrowRight className="w-4 h-4" /></> : <>Zakończ <Check className="w-4 h-4" /></>}
            </button>
          </div>
        )}
      </div>

      <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div
          className="h-full bg-blue-600 transition-all"
          style={{ width: `${(doneCount / total) * 100}%` }}
        />
      </div>
    </div>
  )
}
