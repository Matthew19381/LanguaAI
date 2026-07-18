import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Headphones, Volume2, Check, ArrowRight, RotateCcw, Loader2 } from 'lucide-react'
import { getUserId, getDictation, checkDictation } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'

export default function Dictation() {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [index, setIndex] = useState(0)
  const [typed, setTyped] = useState('')
  const [result, setResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const audioRef = useRef(null)
  const navigate = useNavigate()
  const userId = getUserId()
  const { t } = useLanguage()

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    getDictation(userId, 5)
      .then(data => setItems(data.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [userId])

  const current = items && items[index]

  const play = () => {
    if (!current?.audio_path) return
    if (!audioRef.current) audioRef.current = new Audio(current.audio_path)
    else audioRef.current.src = current.audio_path
    audioRef.current.play().catch(() => {})
  }

  const handleCheck = async () => {
    if (!typed.trim() || !current) return
    setChecking(true)
    try {
      const r = await checkDictation(current.sentence, typed)
      setResult(r)
    } catch {
      setResult(null)
    } finally {
      setChecking(false)
    }
  }

  const next = () => {
    setTyped('')
    setResult(null)
    audioRef.current = null
    setIndex(i => i + 1)
  }

  if (loading) return <PageLoader />

  if (!items || items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto p-4">
        <p className="text-gray-400">{t('dictation.empty')}</p>
      </div>
    )
  }

  const finished = index >= items.length

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-1 text-sky-300">
        <Headphones className="w-6 h-6" /> {t('dictation.title')}
      </h1>
      <p className="text-gray-400 text-sm mb-5">{t('dictation.subtitle')}</p>

      {finished ? (
        <div className="card text-center">
          <Check className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
          <p className="text-emerald-300 font-semibold">{t('dictation.done')}</p>
          <div className="flex gap-2 justify-center mt-4">
            <button className="btn-primary" onClick={() => navigate('/quickmode')}>
              {t('dictation.backToQuick')}
            </button>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs text-gray-500">{index + 1} / {items.length}</span>
          </div>

          {/* Play controls */}
          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={play}
              disabled={!current.audio_path}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-sky-700 hover:bg-sky-600 disabled:opacity-40 text-white font-medium transition-colors"
            >
              <Volume2 className="w-5 h-5" /> {t('dictation.play')}
            </button>
            {!current.audio_path && (
              <span className="text-xs text-amber-400">{t('dictation.noAudio')}</span>
            )}
          </div>

          <textarea
            value={typed}
            onChange={e => setTyped(e.target.value)}
            disabled={!!result}
            rows={2}
            placeholder={t('dictation.placeholder')}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-gray-100 focus:outline-none focus:border-sky-600 disabled:opacity-70"
          />

          {!result ? (
            <button
              onClick={handleCheck}
              disabled={!typed.trim() || checking}
              className="btn-primary w-full mt-3 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {checking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {t('dictation.check')}
            </button>
          ) : (
            <div className="mt-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm text-gray-400">{t('dictation.accuracy')}:</span>
                <span className={`font-bold ${result.accuracy >= 80 ? 'text-emerald-400' : result.accuracy >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                  {result.accuracy}%
                </span>
              </div>
              {/* Word-level diff */}
              <div className="flex flex-wrap gap-1.5 mb-3">
                {result.words.map((w, i) => {
                  const label = w.status === 'missing' ? w.reference
                    : w.status === 'extra' ? w.typed
                    : w.status === 'wrong' ? (w.typed || '—')
                    : w.reference
                  const cls = w.status === 'correct' ? 'bg-emerald-900/40 text-emerald-200'
                    : w.status === 'missing' ? 'bg-gray-700/60 text-gray-400 line-through'
                    : 'bg-red-900/40 text-red-200'
                  return (
                    <span key={i} className={`px-2 py-1 rounded text-sm ${cls}`} title={w.status}>
                      {label}
                      {w.status === 'wrong' && w.reference && (
                        <span className="text-emerald-300 ml-1">→ {w.reference}</span>
                      )}
                    </span>
                  )
                })}
              </div>
              {/* Reference sentence revealed */}
              <p className="text-sm text-gray-300 bg-gray-800/60 rounded-lg p-3 mb-3">
                <span className="text-gray-500">{t('dictation.reference')}: </span>{current.sentence}
              </p>
              <div className="flex gap-2">
                <button onClick={play} className="btn-secondary flex items-center gap-2">
                  <RotateCcw className="w-4 h-4" /> {t('dictation.replay')}
                </button>
                <button onClick={next} className="btn-primary flex items-center gap-2 ml-auto">
                  {t('dictation.next')} <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
