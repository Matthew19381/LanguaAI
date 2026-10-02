import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  BookOpen, FlaskConical, MessageSquare,
  Flame, Star, TrendingUp, ChevronRight, Sparkles,
  Target, Clock, CheckCircle, Brain, Mic, Newspaper, Youtube, Timer, AlertTriangle
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
    const today = new Date().toISOString().slice(0, 10)
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

  return (
    <div className="page-container">
      {/* Greeting */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-1">
          {t('home.welcomeBack')} <span className="gradient-text">{stats?.user?.name || t('home.learner')}</span>!
        </h1>
        <p className="text-gray-400">
          {t('home.learning')} {LANG_DISPLAY[stats?.user?.target_language] || stats?.user?.target_language || t('home.yourLanguage')} — {t('home.level')} {stats?.user?.cefr_level || 'A1'}
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<Flame className="w-6 h-6 text-orange-400" />}
          label={t('home.dayStreak')}
          value={stats?.user?.streak_days || 0}
          color="orange"
        />
        <StatCard
          icon={<Star className="w-6 h-6 text-yellow-400" />}
          label={t('home.totalXP')}
          value={stats?.user?.total_xp || 0}
          color="yellow"
        />
        <StatCard
          icon={<CheckCircle className="w-6 h-6 text-emerald-400" />}
          label={t('home.lessonsDone')}
          value={stats?.lessons?.completed || 0}
          color="emerald"
        />
        <StatCard
          icon={<TrendingUp className="w-6 h-6 text-indigo-400" />}
          label={t('home.avgScore')}
          value={`${stats?.tests?.average_score || 0}%`}
          color="indigo"
        />
      </div>

      {/* Level Progress */}
      {stats?.level_info && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="text-gray-400 text-sm">{t('home.level')} {stats.level_info.level}</span>
              <h3 className="text-lg font-semibold">{stats.level_info.level_name}</h3>
            </div>
            <div className="text-right">
              <span className="text-indigo-400 font-bold">{stats.level_info.xp} XP</span>
              <p className="text-gray-500 text-xs">/{stats.level_info.next_level_xp} {t('home.forNextLevel')}</p>
            </div>
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill bg-indigo-500"
              style={{ width: `${stats.level_info.progress_percent}%` }}
            />
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <h2 className="section-title flex items-center gap-2">
        <Target className="w-5 h-5 text-indigo-400" />
        Aktywności
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <ActionCard
          to="/lesson"
          icon={<BookOpen className="w-8 h-8 text-blue-400" />}
          title={t('home.todayLesson')}
          description={t('home.todayLessonDesc')}
          color="blue"
          xp="+25 XP"
        />
        <ActionCard
          to="/test"
          icon={<FlaskConical className="w-8 h-8 text-purple-400" />}
          title={t('home.dailyTest')}
          description={t('home.dailyTestDesc')}
          color="purple"
          xp="+50 XP"
        />
        <ActionCard
          to="/conversation"
          icon={<MessageSquare className="w-8 h-8 text-emerald-400" />}
          title={t('home.practiceSpeaking')}
          description={t('home.practiceSpeakingDesc')}
          color="emerald"
          xp="+30 XP"
        />
        <ActionCard
          to="/pronunciation"
          icon={<Mic className="w-8 h-8 text-orange-400" />}
          title="Wymowa"
          description="Ćwicz wymowę z AI i analizą audio"
          color="orange"
          xp="+10 XP"
        />
        <ActionCard
          to="/news"
          icon={<Newspaper className="w-8 h-8 text-teal-400" />}
          title="Newsy"
          description="Czytaj uproszczone wiadomości po angielsku"
          color="teal"
          xp="+10 XP"
        />
        <ActionCard
          to="/videos"
          icon={<Youtube className="w-8 h-8 text-red-400" />}
          title="Filmy YouTube"
          description="Oglądaj filmy dopasowane do Twojego poziomu"
          color="red"
          xp="+10 XP"
        />
        <ActionCard
          to="/quickmode"
          icon={<Timer className="w-8 h-8 text-emerald-400" />}
          title="Timer"
          description="15-minutowy plan nauki ze stoperem"
          color="emerald"
          xp=""
        />
        <ActionCard
          to="/errors"
          icon={<AlertTriangle className="w-8 h-8 text-yellow-400" />}
          title="Przegląd błędów"
          description="Ucz się na własnych błędach z testów"
          color="yellow"
          xp=""
        />
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

function StatCard({ icon, label, value, color }) {
  return (
    <div className="card text-center">
      <div className="flex justify-center mb-2">{icon}</div>
      <div className={`text-2xl font-bold text-${color}-400`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function ActionCard({ to, icon, title, description, color, xp }) {
  return (
    <Link to={to} className="card-hover">
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-xl bg-${color}-900/30`}>
          {icon}
        </div>
        <div className="flex-1">
          <h3 className="font-semibold mb-1">{title}</h3>
          <p className="text-gray-400 text-sm mb-2">{description}</p>
          <span className={`badge bg-${color}-900 text-${color}-300`}>{xp}</span>
        </div>
        <ChevronRight className="w-5 h-5 text-gray-600 mt-1" />
      </div>
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
