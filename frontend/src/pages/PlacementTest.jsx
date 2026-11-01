import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ChevronRight, ChevronLeft, CheckCircle, User,
  Globe, BookOpen, AlertCircle
} from 'lucide-react'
import LoadingSpinner from '../components/LoadingSpinner'
import {
  startPlacementTest, submitPlacementTest, createUser, getUser, setUserId, getUserId
} from '../api/client'
import { useLanguage } from '../hooks/useLanguage'

const LANGUAGES = ['German', 'English', 'Spanish', 'Russian', 'Chinese']
const NATIVE_LANGUAGES = ['Polish', 'English', 'German', 'French', 'Spanish', 'Russian', 'Other']

const LANG_DISPLAY = {
  German: 'Niemiecki',
  English: 'Angielski',
  Spanish: 'Hiszpański',
  Russian: 'Rosyjski',
  Chinese: 'Chiński',
  Polish: 'Polski',
  French: 'Francuski',
  Other: 'Inny',
}

const STEPS = {
  SETUP: 'setup',
  TESTING: 'testing',
  SUBMITTING: 'submitting',
  RESULTS: 'results',
}

export default function PlacementTest() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { t } = useLanguage()

  // If redirected from language change, reuse existing user
  const existingUserId = parseInt(searchParams.get('userId') || '0') || getUserId()
  const preselectedLang = searchParams.get('language') || 'German'
  const isLanguageChange = !!searchParams.get('language')

  const [step, setStep] = useState(STEPS.SETUP)
  const [error, setError] = useState('')

  // Setup
  const [name, setName] = useState(localStorage.getItem('userName') || '')
  const [targetLanguage, setTargetLanguage] = useState(preselectedLang)
  const [nativeLanguage, setNativeLanguage] = useState('Polish')

  // Test data
  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [loadingTest, setLoadingTest] = useState(false)

  // Results
  const [results, setResults] = useState(null)
  const [userId, setLocalUserId] = useState(existingUserId || null)

  // Signed in on this device: the test re-levels this account (flashcards and history
  // stay) instead of creating a new one. Before 01.11.2026 a second user was created.
  const [account, setAccount] = useState(null)
  useEffect(() => {
    if (!existingUserId || isLanguageChange) return
    let cancelled = false
    getUser(existingUserId)
      .then(u => {
        if (cancelled || !u?.user_id) return
        setAccount(u)
        if (u.target_language) setTargetLanguage(u.target_language)
      })
      .catch(() => { if (!cancelled) setLocalUserId(null) })  // stale id: new account as before
    return () => { cancelled = true }
  }, [existingUserId, isLanguageChange])

  const handleStartTest = async () => {
    const reuseAccount = isLanguageChange || !!account
    if (!reuseAccount && !name.trim()) {
      setError(t('place.enterName'))
      return
    }
    setError('')
    setLoadingTest(true)

    try {
      let newUserId = userId
      if (!reuseAccount || !newUserId) {
        // Create a new user only without an account on this device
        const userRes = await createUser({
          name: name.trim(),
          native_language: nativeLanguage,
          target_language: targetLanguage
        })
        newUserId = userRes.user_id
        setLocalUserId(newUserId)
      }

      // Start placement test
      const testRes = await startPlacementTest({
        language: targetLanguage,
        native_language: nativeLanguage
      })
      setQuestions(testRes.questions || [])
      setStep(STEPS.TESTING)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingTest(false)
    }
  }

  const handleAnswer = (questionId, answer) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }))
  }

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(i => i + 1)
    }
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(i => i - 1)
    }
  }

  const handleSubmit = async () => {
    if (!userId) { setError('User ID not set'); return }
    setStep(STEPS.SUBMITTING)
    try {
      const res = await submitPlacementTest({
        user_id: userId,
        questions,
        answers,
        language: targetLanguage,
        native_language: nativeLanguage
      })
      setResults(res)
      setStep(STEPS.RESULTS)
    } catch (e) {
      setError(e.message)
      setStep(STEPS.TESTING)
    }
  }

  const handleFinish = () => {
    if (userId) {
      setUserId(userId)
      localStorage.setItem('userName', account?.name || name)
      localStorage.setItem('userLanguage', targetLanguage)
    }
    navigate('/')
  }

  const currentQuestion = questions[currentIndex]
  const answeredCount = Object.keys(answers).length

  return (
    <div className="min-h-screen bg-gray-950 py-8 px-4">
      <div className="max-w-2xl mx-auto">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <BookOpen className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold">{t('place.title')}</h1>
          <p className="text-gray-400 mt-1">{t('place.subtitle')}</p>
        </div>

        {/* Setup Step */}
        {step === STEPS.SETUP && (
          <div className="card">
            <h2 className="text-xl font-semibold mb-6">{t('place.tellUs')}</h2>

            {error && (
              <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-red-300">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            {isLanguageChange && (
              <div className="bg-indigo-900/20 border border-indigo-700/30 rounded-lg p-3 mb-4 text-sm text-indigo-300">
                Test plasujący dla języka: <strong>{LANG_DISPLAY[preselectedLang] || preselectedLang}</strong>
              </div>
            )}
            {account && (
              <div data-testid="placement-account" className="bg-indigo-900/20 border border-indigo-700/30 rounded-lg p-3 mb-4 text-sm text-indigo-300">
                Test dla Twojego konta: <strong>{account.name}</strong> ({LANG_DISPLAY[account.target_language] || account.target_language}).
                Fiszki i ich historia zostają, test ustawi tylko poziom i plan nauki.
              </div>
            )}
            {!isLanguageChange && !account && (
              <div data-testid="placement-have-account" className="bg-gray-800/60 border border-gray-700 rounded-lg p-3 mb-4 text-sm text-gray-300">
                <strong>Masz już konto?</strong> Nie rób testu, bo powstanie nowe, puste konto.
                Otwórz LinguaAI tam, gdzie jesteś zalogowany, wejdź w Profil → „Pokaż link logowania”
                i otwórz ten link na tym urządzeniu. Jeśli adres jest inny, podmień początek linku
                (do <code>/login-as</code>) na adres z paska tej przeglądarki.
              </div>
            )}
            <div className="space-y-4">
              {!isLanguageChange && !account && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    <User className="w-4 h-4 inline mr-1" />
                    {t('place.yourName')}
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder={t('place.namePlaceholder')}
                    value={name}
                    onChange={e => setName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleStartTest()}
                  />
                </div>
              )}

              {!isLanguageChange && !account && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    <Globe className="w-4 h-4 inline mr-1" />
                    {t('place.targetLanguage')}
                  </label>
                  <select
                    className="input-field"
                    value={targetLanguage}
                    onChange={e => setTargetLanguage(e.target.value)}
                  >
                    {LANGUAGES.map(lang => (
                      <option key={lang} value={lang}>{LANG_DISPLAY[lang] || lang}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  {t('place.nativeLanguage')}
                </label>
                <select
                  className="input-field"
                  value={nativeLanguage}
                  onChange={e => setNativeLanguage(e.target.value)}
                >
                  {NATIVE_LANGUAGES.map(lang => (
                    <option key={lang} value={lang}>{LANG_DISPLAY[lang] || lang}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              className="btn-primary w-full mt-6 py-3 flex items-center justify-center gap-2"
              onClick={handleStartTest}
              disabled={loadingTest}
            >
              {loadingTest ? (
                <>
                  <LoadingSpinner size="sm" />
                  {t('place.loading')}
                </>
              ) : (
                <>
                  {t('place.startTest')}
                  <ChevronRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        )}

        {/* Testing Step */}
        {step === STEPS.TESTING && currentQuestion && (
          <div>
            {/* Progress */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">
                  {t('place.question')} {currentIndex + 1} {t('place.of')} {questions.length}
                </span>
                <span className="text-sm text-gray-400">
                  {answeredCount} {t('place.answered')}
                </span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill bg-indigo-500"
                  style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
                />
              </div>
            </div>

            <div className="card mb-4">
              {/* Question type badge */}
              <div className="flex items-center gap-2 mb-4">
                <span className="badge-blue capitalize">{currentQuestion.type}</span>
                {currentQuestion.cefr_hint && (
                  <span className="badge-purple">{currentQuestion.cefr_hint}</span>
                )}
              </div>

              {/* Question */}
              <h3 className="text-lg font-medium mb-6 leading-relaxed">
                {currentQuestion.question}
              </h3>

              {/* Options */}
              <div className="space-y-3">
                {(currentQuestion.options || []).map((option, i) => {
                  const letter = option.split('.')[0]?.trim()
                  const isSelected = answers[currentQuestion.id] === letter
                  return (
                    <div
                      key={i}
                      className={`answer-option ${isSelected ? 'selected' : ''}`}
                      onClick={() => handleAnswer(currentQuestion.id, letter)}
                    >
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${
                        isSelected ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300'
                      }`}>
                        {letter}
                      </div>
                      <span className="flex-1">{option.substring(option.indexOf('.') + 1).trim()}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between">
              <button
                className="btn-secondary flex items-center gap-2"
                onClick={handlePrev}
                disabled={currentIndex === 0}
              >
                <ChevronLeft className="w-4 h-4" />
                {t('place.previous')}
              </button>

              {currentIndex < questions.length - 1 ? (
                <button
                  className="btn-primary flex items-center gap-2"
                  onClick={handleNext}
                >
                  {t('place.next')}
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  className="btn-success flex items-center gap-2"
                  onClick={handleSubmit}
                  disabled={answeredCount === 0}
                >
                  {t('place.submit')}
                  <CheckCircle className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Question dots */}
            <div className="flex flex-wrap gap-1.5 mt-4 justify-center">
              {questions.map((q, i) => (
                <button
                  key={i}
                  className={`w-6 h-6 rounded text-xs font-medium transition-colors ${
                    i === currentIndex
                      ? 'bg-indigo-600 text-white'
                      : answers[q.id]
                      ? 'bg-emerald-700 text-emerald-100'
                      : 'bg-gray-700 text-gray-400'
                  }`}
                  onClick={() => setCurrentIndex(i)}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Submitting Step */}
        {step === STEPS.SUBMITTING && (
          <div className="card text-center py-12">
            <LoadingSpinner size="lg" text={t('place.analyzing')} />
            <p className="text-gray-500 text-sm mt-4">{t('place.loading')}</p>
          </div>
        )}

        {/* Results Step */}
        {step === STEPS.RESULTS && results && (
          <div className="card">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-white">{results.cefr_level}</span>
              </div>
              <h2 className="text-2xl font-bold mb-1">{t('place.yourLevel')} {results.cefr_level}</h2>
              <p className="text-gray-400">Score: {Math.round(results.score)}%</p>
            </div>

            {results.strong_areas?.length > 0 && (
              <div className="mb-4">
                <h3 className="font-medium text-emerald-400 mb-2">{t('place.strongAreas')}</h3>
                <div className="flex flex-wrap gap-2">
                  {results.strong_areas.map((area, i) => (
                    <span key={i} className="badge-green capitalize">{area}</span>
                  ))}
                </div>
              </div>
            )}

            {results.weak_areas?.length > 0 && (
              <div className="mb-4">
                <h3 className="font-medium text-red-400 mb-2">{t('place.weakAreas')}</h3>
                <div className="flex flex-wrap gap-2">
                  {results.weak_areas.map((area, i) => (
                    <span key={i} className="badge-red capitalize">{area}</span>
                  ))}
                </div>
              </div>
            )}

            {results.recommendations && (
              <div className="bg-gray-800 rounded-lg p-4 mb-6">
                <h3 className="font-medium mb-2">{t('place.recommendations')}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{results.recommendations}</p>
              </div>
            )}

            {results.study_plan && (
              <div className="bg-indigo-900/20 border border-indigo-700/30 rounded-lg p-4 mb-6">
                <h3 className="font-medium text-indigo-300 mb-1">{t('place.studyPlan')}</h3>
                <p className="text-gray-400 text-sm">
                  Twój spersonalizowany plan obejmuje {results.study_plan.daily_topics?.length || 30} dni
                  nauki {results.study_plan.language} na poziomie {results.study_plan.cefr_level}.
                </p>
              </div>
            )}

            <button className="btn-primary w-full py-3" onClick={handleFinish}>
              {t('place.startLearning')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
