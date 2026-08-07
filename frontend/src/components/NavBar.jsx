import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import {
  BookOpen, FlaskConical, MessageSquare, LayoutGrid,
  BarChart3, Flame, Star, Brain, Timer, Newspaper, Mic,
  BookmarkPlus, X, Loader2, Video, AlertTriangle, Layers,
  Sun, Moon, Dumbbell, Headphones, UserCircle, Volume2, History, Settings
} from 'lucide-react'
import { getUserId, getStats, addFlashcardAI } from '../api/client'
import { useLanguage } from '../hooks/useLanguage'

function useQuickModeTimer() {
  const getState = () => {
    const startTime = localStorage.getItem('quickmode_start')
    const paused = localStorage.getItem('quickmode_paused_remaining')
    const duration = parseInt(localStorage.getItem('quickmode_duration') || '15') * 60
    if (startTime) {
      const elapsed = Math.floor((Date.now() - parseInt(startTime)) / 1000)
      const remaining = duration - elapsed
      return remaining > 0 ? { active: true, seconds: remaining } : null
    }
    if (paused) return { active: false, seconds: parseInt(paused) }
    return null
  }
  const [state, setState] = useState(getState)
  const intervalRef = useRef(null)

  useEffect(() => {
    intervalRef.current = setInterval(() => setState(getState()), 1000)
    return () => clearInterval(intervalRef.current)
  }, [])

  return state
}

function fmtTimer(s) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

function getDailyTabsNav() {
  try {
    const raw = localStorage.getItem('daily_tabs')
    if (!raw) return []
    const parsed = JSON.parse(raw)
    const today = new Date().toISOString().slice(0, 10)
    if (parsed.date !== today) return []
    return parsed.tabs || []
  } catch { return [] }
}

export default function NavBar({ dailyTabs: dailyTabsProp, dark, onToggleDark }) {
  const location = useLocation()
  const [userStats, setUserStats] = useState(null)
  const userId = getUserId()
  const { t } = useLanguage()
  const quickTimer = useQuickModeTimer()
  const dailyTabs = dailyTabsProp || getDailyTabsNav()
  const dailyProgress = Math.min(100, Math.round((dailyTabs.length / 5) * 100))

  const [flashOpen, setFlashOpen] = useState(false)
  const [flashWord, setFlashWord] = useState('')
  const [flashLoading, setFlashLoading] = useState(false)
  const [flashMsg, setFlashMsg] = useState('')

  const navItems = [
    { to: '/', label: t('nav.home'), icon: LayoutGrid, exact: true },
    { to: '/lesson', label: t('nav.lesson'), icon: BookOpen },
    { to: '/pronunciation', label: t('nav.pronounce'), icon: Mic },
    { to: '/conversation', label: t('nav.speak'), icon: MessageSquare },
    { to: '/flashcards', label: t('nav.flashcards'), icon: Brain },
    // Practice + dictation work offline, so they matter most on a phone
    { to: '/practice', label: t('nav.practice'), icon: Dumbbell },
    { to: '/dictation', label: t('nav.dictation'), icon: Headphones },
    { to: '/read-aloud', label: 'Czytaj', icon: Volume2 },
    { to: '/test', label: t('nav.test'), icon: FlaskConical },
    { to: '/news', label: t('nav.news'), icon: Newspaper },
    { to: '/videos', label: t('nav.videos'), icon: Video },
    { to: '/quickmode', label: t('nav.quickmode'), icon: Timer },
    { to: '/stats', label: t('nav.stats'), icon: BarChart3 },
    { to: '/errors', label: 'Błędy', icon: AlertTriangle },
    { to: '/topics', label: 'Bank wiedzy', icon: Layers },
    { to: '/lesson/history', label: 'Historia', icon: History },
    { to: '/profile', label: 'Profil', icon: UserCircle },
    { to: '/settings', label: 'Ustawienia', icon: Settings },
  ]

  useEffect(() => {
    if (userId) {
      getStats(userId)
        .then(data => setUserStats(data))
        .catch(() => {})
    }
  }, [userId, location.pathname])

  const handleQuickFlash = async () => {
    if (!flashWord.trim() || !userId) return
    setFlashLoading(true)
    setFlashMsg('')
    try {
      const res = await addFlashcardAI(userId, flashWord.trim())
      if (res && res.success === false) {
        setFlashMsg(res.message || 'Już istnieje')
      } else {
        setFlashMsg('Dodano! ✓')
        setFlashWord('')
        setTimeout(() => {
          setFlashMsg('')
          setFlashOpen(false)
        }, 1500)
      }
    } catch (e) {
      setFlashMsg('Błąd: ' + e.message)
    } finally {
      setFlashLoading(false)
    }
  }

  const isActive = (to, exact = false) => {
    if (exact) return location.pathname === to
    return location.pathname.startsWith(to) && to !== '/'
  }

  return (
    <nav className="dark:bg-gray-900 bg-white dark:border-b dark:border-gray-800 border-b border-gray-200 sticky top-0 z-50">
      {/* Daily progress bar */}
      <div className="h-1 dark:bg-gray-800 bg-gray-200 w-full">
        <div
          className="h-1 bg-indigo-500 transition-all duration-500"
          style={{ width: `${dailyProgress}%` }}
          title={`Dzienny postęp: ${dailyProgress}%`}
        />
      </div>
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg dark:text-indigo-400 text-indigo-600 hidden sm:block">LinguaAI</span>
          </Link>

          {/* Navigation Links — scrolls horizontally on phones, where the
              14 icons cannot fit on one row */}
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar min-w-0">
            {navItems.map(({ to, label, icon: Icon, exact }) => (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 shrink-0 ${
                  isActive(to, exact) || (exact && location.pathname === to)
                    ? 'bg-indigo-600 text-white'
                    : 'dark:text-gray-400 text-gray-600 dark:hover:text-gray-100 hover:text-gray-900 dark:hover:bg-gray-800 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden md:block">{label}</span>
              </Link>
            ))}
          </div>

          {/* Right side: stats + dark mode + flash quick-add */}
          <div className="flex items-center gap-2">
            {quickTimer && (
              <Link to="/quickmode" className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold ${quickTimer.active ? 'bg-indigo-900/60 text-indigo-300 animate-pulse' : 'dark:bg-gray-800 bg-gray-100 dark:text-gray-400 text-gray-600'}`} title="QuickMode timer">
                <Timer className="w-4 h-4" />
                <span>{fmtTimer(quickTimer.seconds)}</span>
              </Link>
            )}
            {userStats && (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 dark:bg-gray-800 bg-gray-100 rounded-lg px-3 py-1.5">
                  <Flame className="w-4 h-4 text-orange-400" />
                  <span className="text-sm font-semibold text-orange-400">
                    {userStats.user?.streak_days || 0}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 dark:bg-gray-800 bg-gray-100 rounded-lg px-3 py-1.5">
                  <Star className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm font-semibold text-yellow-400">
                    {userStats.user?.total_xp || 0}
                  </span>
                </div>
                {userStats.user?.cefr_level && (
                  <div className="dark:bg-blue-900 bg-blue-100 dark:text-blue-300 text-blue-700 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium hidden sm:flex">
                    {userStats.user.cefr_level}
                  </div>
                )}
              </div>
            )}

            {!userStats && !userId && (
              <Link to="/placement" className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-1.5 px-4 rounded-lg text-sm transition-colors">
                {t('nav.getStarted')}
              </Link>
            )}

            {/* Dark mode toggle */}
            {onToggleDark && (
              <button
                onClick={onToggleDark}
                className="w-9 h-9 rounded-lg dark:bg-gray-800 bg-gray-100 dark:hover:bg-gray-700 hover:bg-gray-200 dark:border dark:border-gray-700 border border-gray-300 flex items-center justify-center transition-colors"
                title={dark ? 'Tryb jasny' : 'Tryb ciemny'}
              >
                {dark ? <Sun className="w-4 h-4 text-yellow-400" /> : <Moon className="w-4 h-4 text-indigo-500" />}
              </button>
            )}

            {/* Flash quick-add — always visible on desktop */}
            {userId && (
              <div className="relative flex items-center gap-1.5">
                {/* Desktop: inline input */}
                <div className="hidden md:flex items-center gap-1.5 dark:bg-gray-800 bg-gray-100 dark:border dark:border-gray-700 border border-gray-300 rounded-lg px-2 py-1">
                  <BookmarkPlus className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                  <input
                    className="bg-transparent text-sm dark:text-gray-200 text-gray-800 dark:placeholder-gray-500 placeholder-gray-400 outline-none w-28"
                    placeholder="Dodaj fiszkę..."
                    value={flashWord}
                    onChange={e => { setFlashWord(e.target.value); setFlashMsg('') }}
                    onKeyDown={e => e.key === 'Enter' && handleQuickFlash()}
                  />
                  {flashLoading && <Loader2 className="w-3 h-3 animate-spin text-indigo-400 shrink-0" />}
                  {flashMsg && <span className={`text-xs shrink-0 ${flashMsg.includes('Błąd') || flashMsg.includes('już istnieje') ? 'text-red-400' : 'text-emerald-400'}`}>{flashMsg.includes('Dodano') ? '✓' : '!'}</span>}
                </div>
                {/* Mobile: toggle button */}
                <button onClick={() => setFlashOpen(o => !o)} className="md:hidden w-9 h-9 rounded-lg bg-indigo-700 hover:bg-indigo-600 flex items-center justify-center" title="Dodaj fiszkę">
                  <BookmarkPlus className="w-4 h-4 text-white" />
                </button>
                {flashOpen && (
                  <div className="absolute right-0 top-11 dark:bg-gray-800 bg-white dark:border dark:border-indigo-700/50 border border-gray-200 rounded-xl shadow-2xl p-3 w-60 z-50 md:hidden">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-indigo-500">Dodaj fiszkę (AI)</span>
                      <button onClick={() => { setFlashOpen(false); setFlashMsg(''); setFlashWord('') }}><X className="w-3.5 h-3.5 dark:text-gray-500 text-gray-400" /></button>
                    </div>
                    <input className="dark:bg-gray-700 bg-gray-50 dark:border-gray-600 border border-gray-300 dark:text-gray-100 text-gray-800 rounded-lg px-3 py-2 w-full text-sm mb-2 outline-none focus:border-indigo-500" placeholder="Słowo..." value={flashWord} onChange={e => setFlashWord(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleQuickFlash()} autoFocus />
                    {flashMsg && <p className={`text-xs mb-2 ${flashMsg.includes('Błąd') || flashMsg.includes('już istnieje') ? 'text-red-400' : 'text-emerald-400'}`}>{flashMsg}</p>}
                    <button className="w-full py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium flex items-center justify-center gap-1 disabled:opacity-50" onClick={handleQuickFlash} disabled={flashLoading || !flashWord.trim()}>
                      {flashLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <BookmarkPlus className="w-3 h-3" />}
                      Dodaj z AI
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
