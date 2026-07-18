import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  BarChart3, Flame, Star, Trophy, BookOpen,
  FlaskConical, Brain, TrendingUp, Target, Calendar,
  Download, Globe, Lightbulb, CheckCircle, Loader2, Clock
} from 'lucide-react'
import { exportProgressCSV } from '../api/client'
import { getUserId, getStats, getDailyTips, updateUserLanguage, getLanguageProfiles, getStudyPlan, getLessonConcepts, generateConceptFlashcards, getVoiceChatPrompt, getBestStudyTime } from '../api/client'
import { NotificationSettings } from '../components/NotificationManager'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'

export default function Stats() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tips, setTips] = useState([])
  const [tipsLoading, setTipsLoading] = useState(false)
  const [studyPlan, setStudyPlan] = useState(null)
  const [csvLoading, setCsvLoading] = useState(false)
  const [showAllLessons, setShowAllLessons] = useState(false)
  const [changingLanguage, setChangingLanguage] = useState(false)
  const [languageMsg, setLanguageMsg] = useState('')
  const [languageProfiles, setLanguageProfiles] = useState(null)
  const [voiceChatPrompt, setvoiceChatPrompt] = useState(null)
  const [voiceChatLoading, setVoiceChatLoading] = useState(false)
  const [bestTime, setBestTime] = useState(null)
  const [manualAnkiDone, setManualAnkiDone] = useState(() => {
    const today = new Date().toISOString().slice(0, 10)
    return localStorage.getItem('manual_anki_date') === today
  })
  const navigate = useNavigate()
  const userId = getUserId()
  const { lang, setLang, t, targetLanguage } = useLanguage()

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    getStats(userId)
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
    getLanguageProfiles(userId)
      .then(setLanguageProfiles)
      .catch(() => {})
    getStudyPlan(userId).then(setStudyPlan).catch(() => {})
    getBestStudyTime(userId).then(setBestTime).catch(() => {})
  }, [userId])

  useEffect(() => {
    if (!userId) return
    const today = new Date().toISOString().slice(0, 10)
    const cachedDate = localStorage.getItem('tips_date')
    const cachedData = localStorage.getItem('tips_data')
    if (cachedDate === today && cachedData) {
      try {
        setTips(JSON.parse(cachedData))
        return
      } catch {}
    }
    setTipsLoading(true)
    getDailyTips(userId)
      .then(data => {
        const tips = data.tips || []
        setTips(tips)
        localStorage.setItem('tips_date', today)
        localStorage.setItem('tips_data', JSON.stringify(tips))
      })
      .catch(() => {})
      .finally(() => setTipsLoading(false))
  }, [userId])

  const handleDownloadCSV = async () => {
    if (!userId) return
    setCsvLoading(true)
    try {
      const response = await exportProgressCSV(userId)
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `progress_${userId}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('CSV download failed:', e)
    } finally {
      setCsvLoading(false)
    }
  }

  const handleGetVoiceChatPrompt = async () => {
    if (!userId) return
    setVoiceChatLoading(true)
    setvoiceChatPrompt(null)
    try {
      const res = await getVoiceChatPrompt(userId)
      setvoiceChatPrompt(res.prompt || res)
    } catch (e) {
      console.error('Voice chat prompt generation failed:', e)
    } finally {
      setVoiceChatLoading(false)
    }
  }

  const LANGUAGES = ['German', 'English', 'Spanish', 'Russian', 'Chinese']

  const LANG_FLAGS = {
    German: 'đź‡©đź‡Ş',
    English: 'đź‡¬đź‡§',
    Spanish: 'đź‡Şđź‡¸',
    Russian: 'đź‡·đź‡ş',
    Chinese: 'đź‡¨đź‡ł',
  }

  const LANG_NAMES_PL = {
    German: 'Niemiecki',
    English: 'Angielski',
    Spanish: 'HiszpaĹ„ski',
    Russian: 'Rosyjski',
    Chinese: 'ChiĹ„ski',
  }

  const handleChangeLanguage = async (newLanguage) => {
    if (!userId || newLanguage === stats?.user?.target_language) return
    setChangingLanguage(true)
    try {
      const result = await updateUserLanguage(userId, newLanguage)
      // Clear cached data for old language
      localStorage.removeItem('tips_date')
      localStorage.removeItem('tips_data')
      localStorage.removeItem('daily_tabs')
      // Clear lesson + test cache for all languages
      Object.keys(localStorage)
        .filter(k => k.startsWith('lesson_cache_') || k.startsWith('test_cache_'))
        .forEach(k => localStorage.removeItem(k))
      localStorage.setItem('userLanguage', newLanguage)
      if (result.needs_placement) {
        navigate(`/placement?language=${encodeURIComponent(newLanguage)}&userId=${userId}`)
      } else {
        window.location.reload()
      }
    } catch (e) {
      setLanguageMsg('BĹ‚Ä…d: ' + e.message)
      setChangingLanguage(false)
    }
  }

  const handleRegenerateLesson = async () => {
    if (!userId) return
    try {
      await fetch(`/api/lessons/next/${userId}`, { method: 'POST' })
      window.location.href = '/lesson'
    } catch (e) {
      alert('BĹ‚Ä…d: ' + e.message)
    }
  }

  if (loading) return <PageLoader text={t('stats.loading')} />
  if (!stats) return null

  const { user, level_info, lessons, tests, flashcards, error_categories, error_examples, achievements } = stats

  const CATEGORY_LABELS = {
    grammar: 'Gramatyka',
    vocabulary: 'SĹ‚ownictwo',
    word_order: 'Szyk zdania',
    articles: 'Rodzajniki',
    verb_conjugation: 'Koniugacja',
    prepositions: 'Przyimki',
    spelling: 'Pisownia',
    pronunciation: 'Wymowa',
    case: 'Przypadki',
    comprehension: 'Rozumienie',
    syntax: 'SkĹ‚adnia',
    pronunciation_spelling: 'Wymowa/Pisownia',
    fluency: 'PĹ‚ynnoĹ›Ä‡',
    register: 'Rejestr',
    application: 'Zastosowanie',
    conversation: 'Rozmowa',
    unknown: 'Inne',
  }

  const CATEGORY_ADVICE = {
    grammar: 'Popracuj nad zasadami gramatycznymi â€” deklinacje, koniugacje, czasy gramatyczne.',
    vocabulary: 'Rozszerz sĹ‚ownictwo â€” ucz siÄ™ nowych sĹ‚Ăłw w kontekĹ›cie zdaĹ„.',
    word_order: 'Ä†wicz szyk zdania â€” zwrĂłÄ‡ uwagÄ™ na kolejnoĹ›Ä‡ sĹ‚Ăłw w zdaniach podrzÄ™dnych.',
    articles: 'Ucz siÄ™ rodzajnikĂłw i rodzaju gramatycznego rzeczownikĂłw na pamiÄ™Ä‡.',
    verb_conjugation: 'Ä†wicz odmianÄ™ czasownikĂłw â€” szczegĂłlnie nieregularne i modalne.',
    prepositions: 'ZapamiÄ™tuj przyimki z ich przypadkami â€” lista typowych poĹ‚Ä…czeĹ„.',
    spelling: 'Ä†wicz pisowniÄ™ â€” zwrĂłÄ‡ uwagÄ™ na podwĂłjne litery i wyjÄ…tki ortograficzne.',
    pronunciation: 'SĹ‚uchaj native speakerĂłw i powtarzaj na gĹ‚os â€” Ä‡wicz trudne dĹşwiÄ™ki.',
    case: 'Ä†wicz przypadki gramatyczne â€” szczegĂłlnie Akkusativ i Dativ z przyimkami.',
    comprehension: 'Ä†wicz rozumienie ze sĹ‚uchu i z czytania â€” wiÄ™cej ekspozycji na jÄ™zyk.',
    syntax: 'Popracuj nad budowÄ… zdaĹ„ zĹ‚oĹĽonych i spĂłjnikami.',
    pronunciation_spelling: 'Ä†wicz wymowÄ™ i pisowniÄ™ â€” sĹ‚uchaj native speakerĂłw i powtarzaj.',
    fluency: 'MĂłw wiÄ™cej i nie bĂłj siÄ™ bĹ‚Ä™dĂłw â€” liczy siÄ™ pĹ‚ynnoĹ›Ä‡ rozmowy.',
    register: 'Ä†wicz rĂłĹĽne rejestry jÄ™zyka â€” formalny i nieformalny styl.',
    application: 'Ä†wicz zastosowanie wiedzy w praktycznych sytuacjach.',
    conversation: 'Regularnie rozmawiaj z AI â€” rĂłĹĽne tematy i sytuacje.',
  }

  const SUPER_GROUPS = [
    {
      id: 'grammar_group',
      label: 'Gramatyka',
      color: 'purple',
      icon: 'đź“',
      keys: ['grammar', 'word_order', 'articles', 'verb_conjugation', 'prepositions', 'case', 'syntax'],
      advice: 'Skup siÄ™ na zasadach gramatycznych: odmiana czasownikĂłw, przypadki, szyk zdania. Ä†wicz Ä‡wiczenia gramatyczne z lekcji i zaglÄ…daj do wyjaĹ›nieĹ„.',
    },
    {
      id: 'comprehension_group',
      label: 'Rozumienie',
      color: 'blue',
      icon: 'đź“–',
      keys: ['comprehension', 'vocabulary', 'application'],
      advice: 'ZwiÄ™ksz ekspozycjÄ™ na jÄ™zyk â€” czytaj, sĹ‚uchaj, oglÄ…daj. Dodawaj nowe sĹ‚Ăłwka do fiszek i powtarzaj je regularnie.',
    },
    {
      id: 'pronunciation_group',
      label: 'Wymowa',
      color: 'emerald',
      icon: 'đźŽ™ď¸Ź',
      keys: ['pronunciation', 'pronunciation_spelling', 'spelling'],
      advice: 'SĹ‚uchaj native speakerĂłw i naĹ›laduj. Korzystaj z zakĹ‚adki Wymowa â€” nagrywaj siÄ™ i analizuj rĂłĹĽnice.',
    },
    {
      id: 'conversation_group',
      label: 'Rozmowa',
      color: 'yellow',
      icon: 'đź’¬',
      keys: ['fluency', 'register', 'conversation', 'unknown'],
      advice: 'MĂłw regularnie â€” nie bĂłj siÄ™ bĹ‚Ä™dĂłw. Korzystaj z zakĹ‚adki MĂłw: rozmawiaj z AI na rĂłĹĽne tematy, proĹ› o korektÄ™.',
    },
  ]

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <BarChart3 className="w-7 h-7 text-blue-400" />
        <div>
          <h1 className="text-2xl font-bold">{t('stats.title')}</h1>
          <p className="text-gray-400">{user?.name} Â· {LANG_NAMES_PL[user?.target_language] || user?.target_language} Â· {user?.cefr_level}</p>
        </div>
      </div>

      {/* XP & Level */}
      <div className="card mb-6 bg-gradient-to-r from-indigo-900/40 to-purple-900/40 border-indigo-700/30">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-indigo-600 rounded-full flex items-center justify-center">
            <span className="text-xl font-bold">{level_info?.level}</span>
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold">{level_info?.level_name}</h2>
            <p className="text-gray-400 text-sm">
              {t('stats.level')} {level_info?.level}/{level_info?.max_level || 50} Â·{' '}
              {level_info?.xp} / {level_info?.next_level_xp} XP
            </p>
            <div className="progress-bar mt-2">
              <div
                className="progress-fill bg-gradient-to-r from-indigo-500 to-purple-500"
                style={{ width: `${level_info?.progress_percent || 0}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Today's Activity Completion â€” WskaĹşnik ukoĹ„czenia */}
      <div className="card mb-6">
        <h2 className="section-title flex items-center gap-2 mb-3">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          WskaĹşnik ukoĹ„czenia â€” dziĹ›
        </h2>
        <TodayCompletion stats={stats} />
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatBox
          icon={<Flame className="w-6 h-6 text-orange-400" />}
          label={t('stats.streak')}
          value={`${user?.streak_days || 0} ${t('stats.days')}`}
          color="orange"
        />
        <StatBox
          icon={<Star className="w-6 h-6 text-yellow-400" />}
          label={t('stats.totalXP')}
          value={user?.total_xp || 0}
          color="yellow"
        />
        <StatBox
          icon={<BookOpen className="w-6 h-6 text-blue-400" />}
          label={t('stats.lessons')}
          value={`${lessons?.completed || 0}/${lessons?.total || 0}`}
          color="blue"
        />
        <StatBox
          icon={<Trophy className="w-6 h-6 text-emerald-400" />}
          label={t('stats.avgScore')}
          value={`${tests?.average_score || 0}%`}
          color="emerald"
        />
      </div>

      {/* Test Score History List */}
      {tests?.history?.length > 0 && (
        <div className="card mb-6">
          <h2 className="section-title flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-purple-400" />
            {t('stats.testHistory')}
          </h2>
          <div className="space-y-2 mb-3">
            {tests.history.map((item, i) => {
              const pct = Math.round(item.score)
              const color = pct >= 80 ? 'text-emerald-400' : pct >= 60 ? 'text-yellow-400' : 'text-red-400'
              return (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-800 last:border-0">
                  <span className="text-gray-400 text-sm">{item.date}</span>
                  <span className={`text-2xl font-bold ${color}`}>{pct}%</span>
                </div>
              )
            })}
          </div>
          <div className="flex gap-4 text-xs text-gray-500">
            <span>{t('stats.best')} <span className="text-emerald-400">{tests.best_score}%</span></span>
            <span>{t('stats.average')} <span className="text-yellow-400">{tests.average_score}%</span></span>
            <span>{t('stats.testsTaken')} <span className="text-blue-400">{tests.total_taken}</span></span>
          </div>
        </div>
      )}

      {/* Lesson Completion */}
      {lessons?.history?.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="section-title flex items-center gap-2 mb-0">
              <Calendar className="w-5 h-5 text-blue-400" />
              {t('stats.recentLessons')} ({lessons.history.length})
            </h2>
            {lessons.history.length > 7 && (
              <button
                onClick={() => setShowAllLessons(s => !s)}
                className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                {showAllLessons ? 'ZwiĹ„' : 'PokaĹĽ wszystkie'}
              </button>
            )}
          </div>
          <div className="space-y-2">
            {(showAllLessons ? lessons.history : lessons.history.slice(-7)).map((lesson, i) => (
              <Link key={i} to={lesson.id ? `/lesson/${lesson.id}` : '/lesson'} className="flex items-center gap-3 hover:bg-gray-800/40 rounded px-1 py-0.5 transition-colors">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  lesson.completed ? 'bg-emerald-700 text-emerald-100' : 'bg-gray-700 text-gray-400'
                }`}>
                  {lesson.day}
                </div>
                <div className="flex-1">
                  <p className={`text-sm ${lesson.completed ? 'text-gray-300' : 'text-gray-500'}`}>
                    {(lesson.title || '').replace(/^Day\s+\d+[:\s]*/i, '').replace(/^DzieĹ„\s+\d+[:\s]*/i, '') || lesson.title}
                  </p>
                </div>
                <span className="text-xs text-gray-600">{lesson.date}</span>
                {lesson.completed && (
                  <div className="w-4 h-4 text-emerald-400">âś“</div>
                )}
              </Link>
            ))}
          </div>
          {lessons.completion_rate !== undefined && (
            <div className="mt-3 pt-3 border-t border-gray-800">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">{t('stats.completionRate')}</span>
                <span className="text-emerald-400">{lessons.completion_rate}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill bg-emerald-500"
                  style={{ width: `${lessons.completion_rate}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Flashcards Stats */}
      {stats?.flashcards && (
        <div className="card mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Flame className="w-5 h-5 text-orange-400" />
            <h2 className="section-title">{t('stats.flashcardsTitle')}</h2>
          </div>
          <div className="grid grid-cols-3 gap-3 mb-4 text-center">
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-2xl font-bold text-orange-400">{stats.flashcards.total}</div>
              <div className="text-xs text-gray-500 mt-1">{t('stats.totalCards')}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-2xl font-bold text-red-400">{stats.flashcards.due_today}</div>
              <div className="text-xs text-gray-500 mt-1">{t('stats.dueToday')}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-2xl font-bold text-emerald-400">
                {stats.flashcards.total - stats.flashcards.due_today}
              </div>
              <div className="text-xs text-gray-500 mt-1">{t('stats.upToDate') || 'Aktualne'}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/flashcards"
              className="btn-secondary text-sm flex items-center gap-1"
            >
              <Flame className="w-3 h-3" />
              {t('stats.goToFlashcards') || 'PrzejdĹş do fiszek'}
            </Link>
          </div>
          {/* Manual Anki review checkbox */}
          <label className="flex items-center gap-2 mt-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={manualAnkiDone}
              onChange={e => {
                if (e.target.checked) {
                  localStorage.setItem('manual_anki_date', new Date().toISOString().slice(0, 10))
                  setManualAnkiDone(true)
                } else {
                  localStorage.removeItem('manual_anki_date')
                  setManualAnkiDone(false)
                }
              }}
              className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0 cursor-pointer accent-emerald-500"
            />
            <span className="text-sm text-gray-400">
              {manualAnkiDone ? '✓ Powtórzone w Anki' : 'Powtórzone w Anki (ręczne)'}
            </span>
          </label>
        </div>
      )}

      {/* Voice Chat Prompt Generator */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            <h2 className="section-title">{t('stats.voiceChatPrompt') || 'Prompt dla Voice Chat'}</h2>
          </div>
          <button
            onClick={handleGetVoiceChatPrompt}
            disabled={voiceChatLoading}
            className="btn-primary text-sm flex items-center gap-1"
          >
            {voiceChatLoading ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Brain className="w-3 h-3" />
            )}
            {voiceChatLoading ? 'Generowanie...' : 'Wygeneruj prompt'}
          </button>
        </div>
        {voiceChatPrompt?.prompt && (
          <div>
            <div className="bg-gray-800 rounded-lg p-3 mb-3">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
                {voiceChatPrompt.prompt}
              </pre>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(voiceChatPrompt.prompt)
                  alert('Prompt skopiowany do schowka!')
                }}
                className="btn-secondary text-sm flex items-center gap-1"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2M8 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-0z" />
                </svg>
                Kopiuj do schowka
              </button>
              {voiceChatPrompt.has_lesson_today && (
                <span className="text-xs text-emerald-400">âś“ Lekcja dzisiaj ukoĹ„czona</span>
              )}
              {voiceChatPrompt.due_flashcards > 0 && (
                <span className="text-xs text-yellow-400">Fiszki do powtĂłrki: {voiceChatPrompt.due_flashcards}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Lesson Plan / Study Plan */}
      {studyPlan?.plan && (
        <LessonPlanCard plan={studyPlan.plan} currentLesson={studyPlan.current_lesson} />
      )}

      {/* Error Categories */}
      {error_categories && Object.keys(error_categories).length > 0 && (
        <ErrorCategoriesCard
          error_categories={error_categories}
          error_examples={error_examples}
          CATEGORY_LABELS={CATEGORY_LABELS}
          CATEGORY_ADVICE={CATEGORY_ADVICE}
          SUPER_GROUPS={SUPER_GROUPS}
          t={t}
        />
      )}

      {/* Grammar Concepts */}
      <ConceptsCard userId={userId} t={t} />

      {/* Achievements */}
      {achievements && (
        <div className="card mb-6">
          <h2 className="section-title flex items-center gap-2 mb-1">
            <Trophy className="w-5 h-5 text-yellow-400" />
            {t('stats.achievements')}
          </h2>
          <p className="text-gray-500 text-xs mb-4">
            {achievements.earned}/{achievements.total} {t('stats.unlocked')}
          </p>
          <div className="progress-bar mb-4">
            <div
              className="progress-fill bg-yellow-500"
              style={{ width: `${achievements.total ? (achievements.earned / achievements.total) * 100 : 0}%` }}
            />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {achievements.achievements?.map((ach) => {
              const titleKey = `ach.${ach.type}.title`
              const descKey = `ach.${ach.type}.desc`
              const displayTitle = t(titleKey) !== titleKey ? t(titleKey) : ach.title
              const displayDesc = t(descKey) !== descKey ? t(descKey) : ach.description
              return (
                <div
                  key={ach.type}
                  className={`rounded-lg p-3 text-center transition-all ${
                    ach.earned
                      ? 'bg-yellow-900/20 border border-yellow-700/40'
                      : 'bg-gray-800/50 opacity-40'
                  }`}
                  title={displayDesc}
                >
                  <div className="text-2xl mb-1">{ach.icon}</div>
                  <p className={`text-xs font-medium ${ach.earned ? 'text-yellow-300' : 'text-gray-500'}`}>
                    {displayTitle}
                  </p>
                  {ach.earned && ach.unlocked_at && (
                    <p className="text-[10px] text-gray-600 mt-0.5">
                      {new Date(ach.unlocked_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Best study time (SCI-5) */}
      {bestTime?.enough_data && bestTime?.best_bucket && (
        <div className="card mb-6">
          <h2 className="section-title flex items-center gap-2">
            <Clock className="w-5 h-5 text-sky-400" />
            {t('stats.bestTimeTitle')}
          </h2>
          <p className="text-gray-300 text-sm mt-1">
            {t('stats.bestTimeIntro')}{' '}
            <span className="font-semibold text-sky-300">
              {t(`stats.timeBucket.${bestTime.best_bucket}`)}
            </span>.
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            {Object.entries(bestTime.buckets).map(([name, b]) => (
              b.avg_score != null && (
                <div key={name} className={`px-3 py-1.5 rounded-lg text-xs ${
                  name === bestTime.best_bucket
                    ? 'bg-sky-900/40 border border-sky-700/50 text-sky-200'
                    : 'bg-gray-800/60 text-gray-400'
                }`}>
                  {t(`stats.timeBucket.${name}`)}: {b.avg_score}% ({b.n})
                </div>
              )
            ))}
          </div>
        </div>
      )}

      {/* Daily Tips */}
      <div className="card mb-6">
        <h2 className="section-title flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-400" />
          {t('stats.tips')}
        </h2>
        {tipsLoading ? (
          <p className="text-gray-400 text-sm">{t('stats.loadingTips')}</p>
        ) : tips.length === 0 ? (
          <p className="text-gray-400 text-sm">{t('stats.noTips')}</p>
        ) : (
          <div className="space-y-4">
            {tips.map((tip, i) => (
              <div key={i} className="bg-gray-800/60 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                    tip.type === 'grammar' ? 'bg-blue-900/50 text-blue-300' :
                    tip.type === 'vocabulary' ? 'bg-emerald-900/50 text-emerald-300' :
                    tip.type === 'culture' ? 'bg-purple-900/50 text-purple-300' :
                    'bg-yellow-900/50 text-yellow-300'
                  }`}>{
                    tip.type === 'grammar' ? 'Gramatyka' :
                    tip.type === 'vocabulary' ? 'SĹ‚ownictwo' :
                    tip.type === 'culture' ? 'Kultura' :
                    tip.type === 'memory_tip' ? 'ZapamiÄ™tywanie' :
                    tip.type || 'WskazĂłwka'
                  }</span>
                  <p className="font-semibold text-gray-100 text-sm">{tip.title}</p>
                </div>
                <p className="text-gray-300 text-sm leading-relaxed">{tip.content}</p>
                {tip.source && (
                  <p className="text-gray-500 text-xs mt-2 italic">â€” {tip.source}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="card mb-6">
        <h2 className="section-title flex items-center gap-2">
          <Globe className="w-5 h-5 text-indigo-400" />
          {t('stats.settings')}
        </h2>

        {/* UI Language Toggle */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-300 text-sm">{t('stats.uiLanguage')}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setLang('pl')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                lang === 'pl' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'
              }`}
            >
              {t('stats.polishMode')}
            </button>
            {targetLanguage === 'English' ? (
              <button
                onClick={() => setLang('hardcore')}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  lang === 'hardcore' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'
                }`}
              >
                Hardcore (EN)
              </button>
            ) : (
              <span className="px-4 py-1.5 rounded-lg text-sm bg-gray-800/50 text-gray-600" title="DostÄ™pne tylko dla jÄ™zyka angielskiego">
                Hardcore (tylko EN)
              </span>
            )}
          </div>
        </div>

        {/* Target Language Change */}
        <div className="mb-4 mt-4">
          <span className="text-gray-300 text-sm block mb-1">ZmieĹ„ jÄ™zyk nauki</span>
          <span className="text-gray-500 text-xs mb-3 block">Progres dla kaĹĽdego jÄ™zyka jest zachowywany oddzielnie</span>
          <div className="grid grid-cols-5 gap-2">
            {LANGUAGES.map(lng => {
              const profile = languageProfiles?.languages?.find(p => p.language === lng)
              const isActive = user?.target_language === lng
              const cefr = profile?.cefr_level
              const started = profile?.started
              return (
                <button
                  key={lng}
                  onClick={() => handleChangeLanguage(lng)}
                  disabled={changingLanguage || isActive}
                  className={`flex flex-col items-center gap-1 p-2 rounded-lg border text-center transition-all ${
                    isActive
                      ? 'bg-indigo-700/40 border-indigo-500 text-white'
                      : started
                      ? 'bg-gray-800 border-gray-600 text-gray-300 hover:border-indigo-500'
                      : 'bg-gray-900/50 border-gray-800 text-gray-500 hover:border-gray-600'
                  } disabled:cursor-default`}
                >
                  <span className="text-xl">{LANG_FLAGS[lng]}</span>
                  <span className="text-xs font-medium leading-tight">{LANG_NAMES_PL[lng] || lng}</span>
                  {cefr ? (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      isActive ? 'bg-indigo-500 text-white' : 'bg-gray-700 text-gray-300'
                    }`}>{cefr}</span>
                  ) : (
                    <span className="text-[10px] text-gray-600">â€”</span>
                  )}
                  {profile?.lessons_completed > 0 && (
                    <span className="text-[10px] text-gray-500">{profile.lessons_completed} lekcji</span>
                  )}
                </button>
              )
            })}
          </div>
          {changingLanguage && <p className="text-xs text-indigo-400 mt-2">Zmienianie jÄ™zyka...</p>}
          {languageMsg && <p className="text-sm text-indigo-300 mt-2">{languageMsg}</p>}
        </div>

        <button
          onClick={handleRegenerateLesson}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-red-900/30 hover:border-red-700/30 border border-transparent text-gray-300 hover:text-red-300 text-sm transition-colors mt-2"
        >
          Wygeneruj nastÄ™pnÄ… lekcjÄ™
        </button>

      </div>

      {/* Notification Settings */}
      <NotificationSettings />

      {/* Member since */}
      <p className="text-center text-gray-600 text-sm mt-6">
        {t('stats.memberSince')} {user?.member_since}
      </p>
    </div>
  )
}

function ErrorCategoriesCard({ error_categories, error_examples, CATEGORY_LABELS, CATEGORY_ADVICE, SUPER_GROUPS, t }) {
  const [expanded, setExpanded] = useState({})
  const total = Object.values(error_categories).reduce((a, b) => a + b, 0)

  const COLOR_MAP = {
    purple: { bar: 'bg-purple-500', badge: 'bg-purple-900/30 text-purple-300 border-purple-700/40', title: 'text-purple-300' },
    blue: { bar: 'bg-blue-500', badge: 'bg-blue-900/30 text-blue-300 border-blue-700/40', title: 'text-blue-300' },
    emerald: { bar: 'bg-emerald-500', badge: 'bg-emerald-900/30 text-emerald-300 border-emerald-700/40', title: 'text-emerald-300' },
    yellow: { bar: 'bg-yellow-500', badge: 'bg-yellow-900/30 text-yellow-300 border-yellow-700/40', title: 'text-yellow-300' },
  }

  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="section-title flex items-center gap-2">
          <Target className="w-5 h-5 text-red-400" />
          {t('stats.errorAnalysis')}
        </h2>
        <Link to="/errors" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
          PrzeglÄ…d wszystkich bĹ‚Ä™dĂłw â†’
        </Link>
      </div>
      <p className="text-gray-400 text-sm mb-4">{t('stats.errorAreas')}</p>

      <div className="space-y-3">
        {SUPER_GROUPS.map(group => {
          const groupCount = group.keys.reduce((sum, k) => sum + (error_categories[k] || 0), 0)
          const pct = total > 0 ? Math.round((groupCount / total) * 100) : 0
          const isOpen = expanded[group.id]
          const c = COLOR_MAP[group.color]
          const subEntries = group.keys
            .filter(k => error_categories[k] > 0)
            .sort((a, b) => error_categories[b] - error_categories[a])

          return (
            <div key={group.id} className={`rounded-lg border ${groupCount > 0 ? `border-${group.color}-800/40 bg-${group.color}-950/10` : 'border-gray-800/40'}`}>
              <button
                className="w-full text-left p-3"
                onClick={() => setExpanded(e => ({ ...e, [group.id]: !e[group.id] }))}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`font-semibold flex items-center gap-2 ${groupCount > 0 ? c.title : 'text-gray-500'}`}>
                    <span>{group.icon}</span>
                    {group.label}
                    {groupCount > 0 && (
                      <span className={`text-xs px-1.5 py-0.5 rounded border ${c.badge}`}>{groupCount}</span>
                    )}
                  </span>
                  <span className="flex items-center gap-2">
                    {groupCount === 0 && <span className="text-xs text-emerald-500">âś“ brak bĹ‚Ä™dĂłw</span>}
                    <span className="text-gray-600 text-xs">{isOpen ? 'â–˛' : 'â–Ľ'}</span>
                  </span>
                </div>
                {groupCount > 0 && (
                  <div className="progress-bar">
                    <div className={`progress-fill ${c.bar}`} style={{ width: `${pct}%` }} />
                  </div>
                )}
              </button>

              {isOpen && (
                <div className="px-3 pb-3 space-y-2 border-t border-gray-700/30 pt-2">
                  <p className="text-xs text-indigo-300 italic">đź’ˇ {group.advice}</p>
                  {subEntries.length > 0 && (
                    <div className="space-y-1.5 mt-2">
                      {subEntries.map(key => {
                        const count = error_categories[key]
                        const examples = error_examples?.[key] || []
                        const subPct = total > 0 ? Math.round((count / total) * 100) : 0
                        const isSubOpen = expanded[key]
                        return (
                          <div key={key}>
                            <button
                              className="w-full text-left"
                              onClick={e => { e.stopPropagation(); setExpanded(prev => ({ ...prev, [key]: !prev[key] })) }}
                            >
                              <div className="flex justify-between text-xs text-gray-400 mb-0.5">
                                <span className="flex items-center gap-1">
                                  {CATEGORY_LABELS[key] || key}
                                  {(examples.length > 0 || CATEGORY_ADVICE[key]) && (
                                    <span className="text-gray-600">{isSubOpen ? 'â–˛' : 'â–Ľ'}</span>
                                  )}
                                </span>
                                <span className="text-gray-600">{count} ({subPct}%)</span>
                              </div>
                              <div className="h-1 rounded-full bg-gray-700">
                                <div className={`h-1 rounded-full ${c.bar} opacity-60`} style={{ width: `${subPct}%` }} />
                              </div>
                            </button>
                            {isSubOpen && (examples.length > 0 || CATEGORY_ADVICE[key]) && (
                              <div className="mt-1 pl-2 space-y-1">
                                {examples.map((ex, ei) => (
                                  <div key={ei} className="text-xs text-gray-500 flex gap-2">
                                    <span className="text-red-400 shrink-0">âś—</span>
                                    <span className="truncate">{ex.question}</span>
                                    {ex.correct && <span className="text-emerald-500 shrink-0">â†’ {ex.correct}</span>}
                                  </div>
                                ))}
                                {CATEGORY_ADVICE[key] && (
                                  <p className="text-xs text-gray-500 italic">â†’ {CATEGORY_ADVICE[key]}</p>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ConceptsCard({ userId, t }) {
  const [open, setOpen] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [addingIdx, setAddingIdx] = useState(null)
  const [addedIdxs, setAddedIdxs] = useState(new Set())
  const [msg, setMsg] = useState('')

  const load = async () => {
    if (data) { setOpen(o => !o); return }
    setOpen(true)
    setLoading(true)
    try {
      const res = await getLessonConcepts(userId)
      setData(res)
    } catch {
      setData({ concepts: [], lesson_title: null })
    } finally {
      setLoading(false)
    }
  }

  const addToFlash = async (concept, idx) => {
    setAddingIdx(idx)
    try {
      await generateConceptFlashcards(data.lesson_id)
      setAddedIdxs(prev => new Set([...prev, idx]))
      setMsg('Koncepcje dodane do fiszek!')
      setTimeout(() => setMsg(''), 3000)
    } catch {
      setMsg('BĹ‚Ä…d dodawania.')
    } finally {
      setAddingIdx(null)
    }
  }

  return (
    <div className="card mb-6">
      <button className="w-full flex items-center justify-between" onClick={load}>
        <h2 className="section-title flex items-center gap-2 mb-0">
          <BookOpen className="w-5 h-5 text-teal-400" />
          Koncepcje gramatyczne z ostatniej lekcji
        </h2>
        <span className="text-gray-600 text-xs">{open ? 'â–˛' : 'â–Ľ'}</span>
      </button>

      {open && (
        <div className="mt-4">
          {loading && <p className="text-gray-500 text-sm">Generowanie...ncepcji...</p>}
          {data && !loading && (
            <>
              {data.lesson_title && (
                <p className="text-xs text-gray-500 mb-3">Lekcja: <span className="text-gray-300">{data.lesson_title}</span></p>
              )}
              {data.concepts?.length === 0 && (
                <p className="text-gray-500 text-sm">Brak koncepcji gramatycznych w tej lekcji.</p>
              )}
              {data.concepts?.length > 0 && (
                <>
                  <div className="space-y-3 mb-3">
                    {data.concepts.map((c, i) => (
                      <div key={i} className="bg-gray-800/60 rounded-lg p-3 border border-gray-700/40">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <p className="font-semibold text-teal-300 text-sm mb-1">{c.name}</p>
                            <p className="text-gray-400 text-xs leading-relaxed">{c.explanation}</p>
                            {c.example && (
                              <p className="text-yellow-300 text-xs mt-1 italic">PrzykĹ‚ad: {c.example}</p>
                            )}
                          </div>
                          <button
                            onClick={() => addToFlash(c, i)}
                            disabled={addingIdx === i || addedIdxs.has(i)}
                            className={`shrink-0 text-xs px-2 py-1 rounded transition-colors ${addedIdxs.has(i) ? 'bg-emerald-700/30 text-emerald-400' : 'bg-gray-700 hover:bg-teal-700/40 text-gray-400 hover:text-teal-300'}`}
                            title="Dodaj do fiszek"
                          >
                            {addedIdxs.has(i) ? 'âś“' : addingIdx === i ? '...' : '+'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  {msg && <p className="text-emerald-400 text-xs">{msg}</p>}
                  <button
                    onClick={() => { setData(null); setOpen(false); setAddedIdxs(new Set()) }}
                    className="text-xs text-gray-600 hover:text-gray-400 mt-1"
                  >
                    OdĹ›wieĹĽ â†’
                  </button>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

function StatBox({ icon, label, value, color }) {
  return (
    <div className="card text-center">
      <div className="flex justify-center mb-2">{icon}</div>
      <div className={`text-xl font-bold text-${color}-400`}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  )
}

function TodayCompletion({ stats }) {
  const [tabs, setTabs] = useState(() => {
    try {
      const raw = localStorage.getItem('daily_tabs')
      if (!raw) return []
      const parsed = JSON.parse(raw)
      const today = new Date().toISOString().slice(0, 10)
      if (parsed.date !== today) return []
      return parsed.tabs || []
    } catch { return [] }
  })

  // Re-read on visibility change (user switches back to this tab)
  useEffect(() => {
    const refresh = () => {
      try {
        const raw = localStorage.getItem('daily_tabs')
        if (!raw) return setTabs([])
        const parsed = JSON.parse(raw)
        const today = new Date().toISOString().slice(0, 10)
        setTabs(parsed.date === today ? (parsed.tabs || []) : [])
      } catch { setTabs([]) }
    }
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [])

  // Check if lesson completed today
  const lessonDoneToday = stats?.lessons?.history?.some(
    l => l.completed && l.date === new Date().toLocaleDateString('en-US', { month: '2-digit', day: '2-digit' })
  ) || tabs.includes('lesson')

  // Check if test done today
  const testDoneToday = stats?.tests?.history?.some(
    t => t.date === new Date().toLocaleDateString('en-US', { month: '2-digit', day: '2-digit' })
  ) || tabs.includes('test')

  const activities = [
    { key: 'lesson', label: 'Lekcja', icon: 'đź“š', done: lessonDoneToday },
    { key: 'test', label: 'Test', icon: 'đź“ť', done: testDoneToday },
    { key: 'conversation', label: 'Rozmowa', icon: 'đź’¬', done: tabs.includes('conversation') },
    { key: 'flashcards', label: 'Fiszki', icon: 'đźŽ´', done: tabs.includes('flashcards') },
    { key: 'news', label: 'Newsy/Wymowa', icon: 'đź“°', done: tabs.includes('news') || tabs.includes('pronunciation') || tabs.includes('videos') },
  ]

  const doneCount = activities.filter(a => a.done).length
  const pct = Math.round((doneCount / activities.length) * 100)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-400 text-sm">{doneCount}/{activities.length} aktywnoĹ›ci ukoĹ„czonych</span>
        <span className={`text-sm font-bold ${pct === 100 ? 'text-emerald-400' : pct >= 50 ? 'text-yellow-400' : 'text-gray-400'}`}>{pct}%</span>
      </div>
      <div className="progress-bar mb-4">
        <div className={`progress-fill ${pct === 100 ? 'bg-emerald-500' : 'bg-indigo-500'}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {activities.map(act => (
          <div key={act.key} className={`flex flex-col items-center gap-1 p-2 rounded-lg border text-center ${
            act.done
              ? 'bg-emerald-900/20 border-emerald-700/40'
              : 'bg-gray-800/50 border-gray-700/40'
          }`}>
            <span className="text-xl">{act.icon}</span>
            <span className={`text-xs font-medium ${act.done ? 'text-emerald-400' : 'text-gray-500'}`}>{act.label}</span>
            <span className={`text-xs ${act.done ? 'text-emerald-400' : 'text-gray-600'}`}>{act.done ? 'âś“' : 'â€”'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function LessonPlanCard({ plan, currentLesson }) {
  const [expanded, setExpanded] = useState(false)

  // Support both formats: plan.weeks[] and plan.daily_topics[]
  const weeks = plan?.weeks || []
  const dailyTopics = plan?.daily_topics || []
  const weeklyGoals = plan?.weekly_goals || []

  // Group daily_topics into weeks of 7
  const groupedWeeks = weeks.length > 0 ? weeks : weeklyGoals.map((goal, wi) => {
    const weekDays = dailyTopics.filter(d => (wi * 7) < d.day && d.day <= (wi + 1) * 7)
    return { week: goal.week || wi + 1, goal: goal.goal, key_grammar: goal.key_grammar, days: weekDays }
  })

  return (
    <div className="card mb-6">
      <button
        className="w-full flex items-center justify-between"
        onClick={() => setExpanded(e => !e)}
      >
        <h2 className="section-title flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-400" />
          Plan nauki
        </h2>
        <span className="text-gray-500 text-sm">{expanded ? 'â–˛' : 'â–Ľ'}</span>
      </button>
      {expanded && (
        <div className="mt-4 space-y-4">
          {groupedWeeks.length > 0 ? (
            groupedWeeks.map((week, wi) => (
              <div key={wi}>
                <h3 className="text-sm font-semibold text-indigo-300 mb-1">
                  TydzieĹ„ {week.week || wi + 1}{week.goal ? `: ${week.goal}` : (week.theme || week.focus ? `: ${week.theme || week.focus}` : '')}
                </h3>
                {week.key_grammar && (
                  <p className="text-xs text-gray-500 mb-2">Gramatyka: {week.key_grammar}</p>
                )}
                <div className="space-y-1">
                  {(week.days || week.lessons || []).map((day, di) => (
                    <div key={di} className={`flex items-start gap-2 text-sm py-1 border-b border-gray-800 last:border-0 ${currentLesson === day.day ? 'bg-indigo-900/20 rounded px-1' : ''}`}>
                      <span className="text-gray-600 shrink-0 w-16 text-xs">DzieĹ„ {day.day || di + 1}</span>
                      <div className="flex-1">
                        <span className="text-gray-300">{day.grammar_topic || day.topic || day.title || ''}</span>
                        {day.vocabulary_theme && <span className="text-gray-500 text-xs ml-2">Â· {day.vocabulary_theme}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          ) : dailyTopics.length > 0 ? (
            <div className="space-y-1">
              {dailyTopics.map((day) => (
                <div key={day.day} className={`flex items-start gap-2 text-sm py-1 border-b border-gray-800 last:border-0 ${currentLesson === day.day ? 'bg-indigo-900/20 rounded px-1' : ''}`}>
                  <span className="text-gray-600 shrink-0 w-16 text-xs">DzieĹ„ {day.day}</span>
                  <div className="flex-1">
                    <span className="text-gray-300">{day.grammar_topic}</span>
                    {day.vocabulary_theme && <span className="text-gray-500 text-xs ml-2">Â· {day.vocabulary_theme}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

