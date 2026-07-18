import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Dumbbell, Check, X, ArrowRight, Sparkles, Loader2, Shuffle, RotateCcw,
} from 'lucide-react'
import {
  getUserId, getPracticeSet, answerExercise, generateExerciseVariants, getExerciseStats,
} from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'

const SET_SIZE = 10

export default function Practice() {
  const [set, setSet] = useState(null)
  const [loading, setLoading] = useState(true)
  const [index, setIndex] = useState(0)
  const [typed, setTyped] = useState('')
  const [result, setResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState('')
  // Weak skills recomputed after the session — the ones loaded with the set
  // predate the mistakes the learner just made.
  const [weakSkills, setWeakSkills] = useState([])
  const navigate = useNavigate()
  const userId = getUserId()
  const { t } = useLanguage()

  const load = (includeNew = false) => {
    setLoading(true)
    return getPracticeSet(userId, { size: SET_SIZE, includeNew })
      .then(data => {
        setSet(data)
        setIndex(0)
        setTyped('')
        setResult(null)
        setScore({ correct: 0, total: 0 })
        setWeakSkills(data.weak_skills || [])
      })
      .catch(() => setSet(null))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    load()
  }, [userId])

  const exercises = set?.exercises || []
  const current = exercises[index]
  const finished = exercises.length > 0 && index >= exercises.length

  const handleCheck = async () => {
    if (!typed.trim() || !current) return
    setChecking(true)
    try {
      const r = await answerExercise(current.id, userId, typed)
      setResult(r)
      setScore(s => ({ correct: s.correct + (r.correct ? 1 : 0), total: s.total + 1 }))
    } catch {
      setResult(null)
    } finally {
      setChecking(false)
    }
  }

  const next = () => {
    setTyped('')
    setResult(null)
    const upcoming = index + 1
    setIndex(upcoming)
    // Session just ended — refresh weak skills so the suggestion reflects the
    // mistakes made in THIS session, not the state before it started.
    if (upcoming >= exercises.length) {
      getExerciseStats(userId)
        .then(s => setWeakSkills(s.weak_skills || []))
        .catch(() => {})
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setGenMsg('')
    try {
      const r = await generateExerciseVariants(userId, weakSkills.length ? weakSkills : undefined)
      setGenMsg(r.added > 0 ? t('practice.generated').replace('{n}', r.added) : t('practice.nothingGenerated'))
      if (r.added > 0) await load()
    } catch {
      setGenMsg(t('practice.generateFailed'))
    } finally {
      setGenerating(false)
    }
  }

  if (loading) return <PageLoader />

  // Empty bank — exercises are filled by generating lessons
  if (!set || exercises.length === 0) {
    return (
      <div className="max-w-2xl mx-auto p-4">
        <h1 className="text-2xl font-bold flex items-center gap-2 mb-1 text-indigo-300">
          <Dumbbell className="w-6 h-6" /> {t('practice.title')}
        </h1>
        <div className="card mt-4 text-center">
          <p className="text-gray-300">{t('practice.emptyBank')}</p>
          <div className="flex gap-2 justify-center mt-4 flex-wrap">
            <button className="btn-primary" onClick={() => navigate('/lesson')}>
              {t('practice.goToLesson')}
            </button>
            {weakSkills.length > 0 && (
              <button className="btn-secondary flex items-center gap-2" onClick={handleGenerate} disabled={generating}>
                {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {t('practice.generateForWeak')}
              </button>
            )}
          </div>
          {genMsg && <p className="text-sm text-gray-400 mt-3">{genMsg}</p>}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-1 text-indigo-300">
        <Dumbbell className="w-6 h-6" /> {t('practice.title')}
      </h1>
      <p className="text-gray-400 text-sm mb-4">{t('practice.subtitle')}</p>

      {/* Where this set came from */}
      <div className="flex flex-wrap gap-2 mb-4 text-xs">
        <span className="px-2.5 py-1 rounded-lg bg-indigo-900/40 text-indigo-200">
          {t('practice.due')}: {set.due_count}
        </span>
        {set.interleaved_count > 0 && (
          <span className="px-2.5 py-1 rounded-lg bg-purple-900/40 text-purple-200 flex items-center gap-1">
            <Shuffle className="w-3 h-3" /> {t('practice.interleaved')}: {set.interleaved_count}
          </span>
        )}
        {set.generated_new > 0 && (
          <span className="px-2.5 py-1 rounded-lg bg-emerald-900/40 text-emerald-200">
            {t('practice.new')}: {set.generated_new}
          </span>
        )}
      </div>

      {finished ? (
        <div className="card text-center">
          <Check className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
          <p className="text-emerald-300 font-semibold">
            {t('practice.done')} {score.correct}/{score.total}
          </p>
          {weakSkills.length > 0 && (
            <div className="mt-4">
              <p className="text-sm text-gray-400 mb-2">
                {t('practice.weakSkills')}: {weakSkills.join(', ')}
              </p>
              <button
                className="btn-secondary flex items-center gap-2 mx-auto"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {t('practice.generateForWeak')}
              </button>
            </div>
          )}
          {genMsg && <p className="text-sm text-gray-400 mt-3">{genMsg}</p>}
          <div className="flex gap-2 justify-center mt-4 flex-wrap">
            <button className="btn-primary flex items-center gap-2" onClick={() => load()}>
              <RotateCcw className="w-4 h-4" /> {t('practice.again')}
            </button>
            <button className="btn-secondary" onClick={() => navigate('/quickmode')}>
              {t('practice.backToQuick')}
            </button>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-gray-500">{index + 1} / {exercises.length}</span>
            {current.skill_tag && (
              <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">
                {current.skill_tag}
              </span>
            )}
          </div>

          {current.instruction && (
            <p className="text-gray-400 text-sm mb-2">{current.instruction}</p>
          )}
          <p className="text-gray-100 text-lg mb-4">{current.prompt}</p>

          <input
            type="text"
            value={typed}
            onChange={e => setTyped(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !result) handleCheck() }}
            disabled={!!result}
            placeholder={t('practice.placeholder')}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-gray-100 focus:outline-none focus:border-indigo-600 disabled:opacity-70"
          />

          {!result ? (
            <button
              onClick={handleCheck}
              disabled={!typed.trim() || checking}
              className="btn-primary w-full mt-3 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {checking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {t('practice.check')}
            </button>
          ) : (
            <div className="mt-4">
              <div className={`flex items-center gap-2 mb-2 font-semibold ${result.correct ? 'text-emerald-400' : 'text-red-400'}`}>
                {result.correct ? <Check className="w-5 h-5" /> : <X className="w-5 h-5" />}
                {result.correct ? t('practice.correct') : t('practice.wrong')}
              </div>
              {!result.correct && (
                <p className="text-sm text-gray-300 bg-gray-800/60 rounded-lg p-3 mb-2">
                  <span className="text-gray-500">{t('practice.expected')}: </span>
                  <span className="text-emerald-300">{result.expected_answer}</span>
                </p>
              )}
              {result.feedback && (
                <p className="text-sm text-gray-400 mb-3">{result.feedback}</p>
              )}
              <p className="text-xs text-gray-500 mb-3">
                {t('practice.nextReview')}: {result.interval_days} {t('practice.days')}
              </p>
              <button onClick={next} className="btn-primary w-full flex items-center justify-center gap-2">
                {t('practice.next')} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
