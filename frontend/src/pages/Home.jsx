import { useState, useEffect } from 'react'
import { localDay } from '../utils/localDay'
import { Link, useNavigate } from 'react-router-dom'
import {
  BookOpen, FlaskConical, MessageSquare,
  Star, TrendingUp, ChevronRight, Sparkles,
  Target, CheckCircle, Mic, Newspaper, Youtube, Timer, AlertTriangle, GraduationCap
} from 'lucide-react'
import { getUserId, getStats, getDailyTips } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'

const LANG_DISPLAY = {
  German: 'Niemiecki', English: 'Angielski', Spanish: 'Hiszpański',
  Russian: 'Rosyjski', Chinese: 'Chiński',
}

export default function Home() {
  const [stats, setStats] = useState(null)
  const [tips, setTips] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const userId = getUserId()
  const { t } = useLanguage()

  useEffect(() => {
    if (!userId) {
      setLoading(false)
      return
    }
    const today = localDay()
    const cachedDate = localStorage.getItem('tips_date')
    const cachedData = localStorage.getItem('tips_data')
    const hasCachedTips = cachedDate === today && cachedData

    // The dashboard waits only for stats. Tips are an AI call (often tens of
    // seconds on the first visit of the day per device), so they fill in later.
    getStats(userId)
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))

    if (hasCachedTips) {
      try { setTips(JSON.parse(cachedData)) } catch {}
    } else {
      getDailyTips(userId)
        .then(tipsData => {
          const tipsArr = tipsData?.tips || []
          setTips(tipsArr)
          localStorage.setItem('tips_date', today)
          localStorage.setItem('tips_data', JSON.stringify(tipsArr))
        })
        .catch(() => {})
    }
  }, [userId])

  if (loading) return <PageLoader text={t('home.loadingDashboard')} />

  if (!userId) {
    return <WelcomeScreen t={t} />
  }

  const weekDays = stats?.user?.week_days?.days ?? 0
  const weekGoal = stats?.user?.week_days?.goal ?? 5
  const level = stats?.level_info

  return (
    <div className="page-container">
      {/* Greeting */}
      <div className="mb-5">
        <h1 className="text-2xl sm:text-3xl font-bold mb-1">
          {t('home.welcomeBack')} <span className="dark:text-indigo-300 text-indigo-700">{stats?.user?.name || t('home.learner')}</span>!
        </h1>
        <p className="dark:text-gray-300 text-gray-600">
          {t('home.learning')} {LANG_DISPLAY[stats?.user?.target_language] || stats?.user?.target_language || t('home.yourLanguage')} — {t('home.level')} {stats?.user?.cefr_level || 'A1'}
        </p>
      </div>

      {/* Today: one main action first (the lesson), then the week goal */}
      <section className="card mb-5" aria-labelledby="home-today">
        <h2 id="home-today" className="sr-only">Dziś</h2>
        <Link to="/lesson"
          className="flex items-center gap-4 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white p-4 min-h-[72px] transition-colors">
          <span className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/15 shrink-0">
            <BookOpen className="w-6 h-6" aria-hidden="true" />
          </span>
          <span className="flex-1 min-w-0">
            <span className="block text-lg font-semibold leading-snug">{t('home.todayLesson')}</span>
            <span className="block text-sm text-indigo-100">{t('home.todayLessonDesc')} · +25 XP</span>
          </span>
          <ChevronRight className="w-6 h-6 shrink-0" aria-hidden="true" />
        </Link>

        <div className="mt-4">
          <div className="flex items-baseline justify-between mb-2">
            <span className="text-sm dark:text-gray-300 text-gray-600">{t('home.weekDays')}</span>
            <span className="text-lg font-bold tabular-nums dark:text-orange-300 text-orange-800">{`${weekDays} / ${weekGoal}`}</span>
          </div>
          <div className="flex gap-1.5" aria-hidden="true">
            {Array.from({ length: weekGoal }, (_, i) => (
              <span key={i} className={`h-2 flex-1 rounded-full ${i < weekDays ? 'bg-orange-500' : 'dark:bg-gray-800 bg-gray-200'}`} />
            ))}
          </div>
        </div>
      </section>

      {/* Stats: compact, 3 per row on phones */}
      <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-5">
        <StatCard
          icon={<Star className="w-5 h-5 dark:text-yellow-300 text-yellow-800" />}
          label={t('home.totalXP')}
          value={stats?.user?.total_xp || 0}
          valueClass="dark:text-yellow-300 text-yellow-800"
        />
        <StatCard
          icon={<CheckCircle className="w-5 h-5 dark:text-emerald-300 text-emerald-700" />}
          label={t('home.lessonsDone')}
          value={stats?.lessons?.completed || 0}
          valueClass="dark:text-emerald-300 text-emerald-700"
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5 dark:text-indigo-300 text-indigo-700" />}
          label={t('home.avgScore')}
          value={`${stats?.tests?.average_score || 0}%`}
          valueClass="dark:text-indigo-300 text-indigo-700"
        />
      </div>

      {/* Level Progress */}
      {level && (
        <div className="card mb-6">
          <div className="flex items-center justify-between gap-3 mb-2">
            <div className="min-w-0">
              <span className="dark:text-gray-400 text-gray-600 text-sm">{t('home.level')} {level.level}</span>
              <h3 className="text-lg font-semibold">{level.level_name}</h3>
            </div>
            <div className="text-right shrink-0">
              <span className="dark:text-indigo-300 text-indigo-700 font-bold tabular-nums">{level.xp} XP</span>
              <p className="dark:text-gray-400 text-gray-600 text-xs tabular-nums">/{level.next_level_xp} {t('home.forNextLevel')}</p>
            </div>
          </div>
          <div className="progress-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100}
            aria-valuenow={level.progress_percent} aria-label="Postęp do następnego poziomu">
            <div className="progress-fill bg-indigo-500" style={{ width: `${level.progress_percent}%` }} />
          </div>
        </div>
      )}

      {/* Other activities. XP only where the backend awards it:
          test min(50, score/2), conversation min(30, score·0.3) — Wymowa,
          Newsy, Filmy, Timer and Błędy award none (checked 1.11.2026). */}
      <h2 className="section-title flex items-center gap-2">
        <Target className="w-5 h-5 dark:text-indigo-300 text-indigo-700" aria-hidden="true" />
        Aktywności
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 sm:gap-3 mb-8">
        <ActionCard to="/test" icon={FlaskConical} tone="purple"
          title={t('home.dailyTest')} description={t('home.dailyTestDesc')} xp="do 50 XP" />
        <ActionCard to="/conversation" icon={MessageSquare} tone="emerald"
          title={t('home.practiceSpeaking')} description={t('home.practiceSpeakingDesc')} xp="do 30 XP" />
        {/* The mock exam is German-only (backend/routers/exam.py returns 400 otherwise) */}
        {stats?.user?.target_language === 'German' && (
          <ActionCard to="/exam" icon={GraduationCap} tone="blue"
            title="Próbny egzamin B1" description="Sprechen: 3 części, punkty jak na egzaminie Goethe" />
        )}
        <ActionCard to="/pronunciation" icon={Mic} tone="orange"
          title="Wymowa" description="Ćwicz wymowę z AI i analizą audio" />
        <ActionCard to="/news" icon={Newspaper} tone="teal"
          title="Newsy" description="Uproszczone wiadomości w języku, którego się uczysz" />
        <ActionCard to="/videos" icon={Youtube} tone="red"
          title="Filmy YouTube" description="Filmy dopasowane do Twojego poziomu" />
        <ActionCard to="/quickmode" icon={Timer} tone="emerald"
          title="Timer" description="15-minutowy plan nauki ze stoperem" />
        <ActionCard to="/errors" icon={AlertTriangle} tone="yellow"
          title="Przegląd błędów" description="Ucz się na własnych błędach z testów" />
      </div>

      {/* Daily Tips */}
      {tips.length > 0 && (
        <div className="mb-6">
          <h2 className="section-title flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-400" />
            {t('home.dailyTips')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tips.slice(0, 4).map((tip, i) => (
              <TipCard key={i} tip={tip} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function WelcomeScreen({ t }) {
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="text-center max-w-2xl">
        <div className="w-20 h-20 bg-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6 xp-glow">
          <BookOpen className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-4xl font-bold mb-4">
          {t('home.welcomeTitle')} <span className="gradient-text">{t('home.welcomeTitleHighlight')}</span>
        </h1>
        <p className="text-gray-400 text-lg mb-8 leading-relaxed">
          {t('home.welcomeSubtitle')}
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { icon: '📚', labelKey: 'home.featureLessons' },
            { icon: '✍️', labelKey: 'home.featureTests' },
            { icon: '🃏', labelKey: 'home.featureFlashcards' },
            { icon: '💬', labelKey: 'home.featureConversation' },
          ].map((f, i) => (
            <div key={i} className="card text-center py-4">
              <div className="text-3xl mb-2">{f.icon}</div>
              <p className="text-sm text-gray-400">{t(f.labelKey)}</p>
            </div>
          ))}
        </div>

        <Link to="/placement" className="btn-primary text-lg py-3 px-8 inline-flex items-center gap-2">
          {t('home.startTest')}
          <ChevronRight className="w-5 h-5" />
        </Link>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, valueClass }) {
  return (
    <div className="card !p-3 sm:!p-5 text-center">
      <div className="flex justify-center mb-1" aria-hidden="true">{icon}</div>
      <div className={`text-xl sm:text-2xl font-bold tabular-nums ${valueClass}`}>{value}</div>
      <div className="text-xs dark:text-gray-400 text-gray-600 mt-0.5 leading-tight">{label}</div>
    </div>
  )
}

// Full class names (not `bg-${color}-900`): Tailwind only generates classes it
// finds written out, so the old dynamic badge/icon backgrounds were missing.
const TONES = {
  purple: 'dark:bg-purple-500/15 bg-purple-100 dark:text-purple-300 text-purple-700',
  emerald: 'dark:bg-emerald-500/15 bg-emerald-100 dark:text-emerald-300 text-emerald-700',
  blue: 'dark:bg-blue-500/15 bg-blue-100 dark:text-blue-300 text-blue-700',
  orange: 'dark:bg-orange-500/15 bg-orange-100 dark:text-orange-300 text-orange-800',
  teal: 'dark:bg-teal-500/15 bg-teal-100 dark:text-teal-300 text-teal-700',
  red: 'dark:bg-red-500/15 bg-red-100 dark:text-red-300 text-red-700',
  yellow: 'dark:bg-yellow-500/15 bg-yellow-100 dark:text-yellow-300 text-yellow-800',
}

function ActionCard({ to, icon: Icon, tone, title, description, xp }) {
  return (
    <Link to={to} className="card-hover !p-3 sm:!p-4 flex items-center gap-3 min-h-[64px]">
      <span className={`flex items-center justify-center w-11 h-11 rounded-xl shrink-0 ${TONES[tone]}`} aria-hidden="true">
        <Icon className="w-6 h-6" />
      </span>
      <span className="flex-1 min-w-0">
        <span className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold">{title}</span>
          {xp && <span className="badge dark:bg-gray-800 bg-gray-100 dark:text-gray-200 text-gray-700">{xp}</span>}
        </span>
        <span className="block dark:text-gray-400 text-gray-600 text-sm leading-snug">{description}</span>
      </span>
      <ChevronRight className="w-5 h-5 dark:text-gray-500 text-gray-400 shrink-0" aria-hidden="true" />
    </Link>
  )
}

function TipCard({ tip }) {
  const typeColors = {
    grammar: 'blue',
    vocabulary: 'green',
    culture: 'yellow',
    memory_tip: 'purple'
  }
  const color = typeColors[tip.type] || 'gray'

  return (
    <div className="card">
      <div className="flex items-start gap-3">
        <span className={`badge-${color === 'gray' ? 'blue' : color} mt-0.5 shrink-0`}>
          {tip.type === 'grammar' ? 'Gramatyka' :
           tip.type === 'vocabulary' ? 'Słownictwo' :
           tip.type === 'culture' ? 'Kultura' :
           tip.type === 'memory_tip' ? 'Zapamiętywanie' :
           tip.type?.replace('_', ' ') || 'Wskazówka'}
        </span>
        <div>
          <h4 className="font-medium mb-1">{tip.title}</h4>
          <p className="text-gray-400 text-sm leading-relaxed">{tip.content}</p>
        </div>
      </div>
    </div>
  )
}
