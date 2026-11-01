import { Link, useLocation } from 'react-router-dom'
import { localDay } from '../utils/localDay'
import { useState, useEffect, useRef } from 'react'
import {
  BookOpen, FlaskConical, MessageSquare, LayoutGrid,
  BarChart3, Star, Brain, Timer, Newspaper, Mic,
  BookmarkPlus, X, Loader2, Video, AlertTriangle, Layers,
  Sun, Moon, Dumbbell, Headphones, UserCircle, Volume2, History, Settings, GraduationCap, CalendarCheck, Languages,
  LayoutList
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
    const today = localDay()
    if (parsed.date !== today) return []
    return parsed.tabs || []
  } catch { return [] }
}

export default function NavBar({ dailyTabs: dailyTabsProp, dark, onToggleDark, onOpenTranslator }) {
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
  // Phones: the full grouped list lives in the "Wszystko" sheet of the bottom bar
  const [allOpen, setAllOpen] = useState(false)
  useEffect(() => { setAllOpen(false) }, [location.pathname])
  useEffect(() => {
    if (!allOpen) return
    const onKey = (e) => { if (e.key === 'Escape') setAllOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [allOpen])

  // Every function gets a permanently-visible label, grouped by purpose, so
  // nothing is discoverable only by hovering/scrolling/opening a menu — this
  // was raised repeatedly (docs/BACKLOG_UX_2026-08.md P3-1) and previously
  // only half-fixed (missing pages were added, but labels still vanished
  // below `md` and everything lived in one horizontally-scrolling row).
  const navGroups = [
    {
      label: 'Nauka',
      items: [
        { to: '/', label: t('nav.home'), icon: LayoutGrid, exact: true },
        { to: '/lesson', label: t('nav.lesson'), icon: BookOpen },
        { to: '/test', label: t('nav.test'), icon: FlaskConical },
        { to: '/conversation', label: t('nav.speak'), icon: MessageSquare },
        { to: '/pronunciation', label: t('nav.pronounce'), icon: Mic },
        { to: '/exam', label: 'Egzamin B1', icon: GraduationCap },
        { to: '/news', label: t('nav.news'), icon: Newspaper },
        { to: '/topics', label: 'Bank wiedzy', icon: Layers },
      ],
    },
    {
      label: 'Ćwiczenia',
      items: [
        { to: '/flashcards', label: t('nav.flashcards'), icon: Brain },
        { to: '/practice', label: t('nav.practice'), icon: Dumbbell },
        { to: '/dictation', label: t('nav.dictation'), icon: Headphones },
        { to: '/read-aloud', label: 'Czytaj', icon: Volume2 },
        { to: '/quickmode', label: t('nav.quickmode'), icon: Timer },
      ],
    },
    {
      label: 'Media',
      items: [
        { to: '/videos', label: t('nav.videos'), icon: Video },
      ],
    },
    {
      label: 'Postępy',
      items: [
        { to: '/stats', label: t('nav.stats'), icon: BarChart3 },
        { to: '/errors', label: 'Błędy', icon: AlertTriangle },
        { to: '/lesson/history', label: 'Historia', icon: History },
      ],
    },
    {
      label: 'Konto',
      items: [
        { to: '/profile', label: 'Profil', icon: UserCircle },
        { to: '/settings', label: 'Ustawienia', icon: Settings },
      ],
    },
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

  // Phones (below `md`): a compact sticky header with stats and tools, and a
  // bottom bar with 5 labelled buttons in the thumb zone; "Wszystko" opens the
  // complete grouped list, every function with its text label (P3-1 DoD:
  // each function reachable with a readable label). Before 1.11.2026 the
  // grouped links wrapped to ~6 rows and took ~60% of the first phone screen
  // on every page. From `md` up the grouped links stay visible under the header.
  const bottomItems = [
    { to: '/', label: t('nav.home'), icon: LayoutGrid, exact: true },
    { to: '/lesson', label: t('nav.lesson'), icon: BookOpen },
    { to: '/flashcards', label: t('nav.flashcards'), icon: Brain },
    { to: '/conversation', label: t('nav.speak'), icon: MessageSquare },
  ]
  const weekDays = userStats?.user?.week_days
  const iconBtn = 'w-11 h-11 rounded-xl dark:bg-gray-800 bg-gray-100 dark:hover:bg-gray-700 hover:bg-gray-200 flex items-center justify-center transition-colors'

  return (
    <>
    <header className="dark:bg-gray-900/95 bg-white/95 backdrop-blur sticky top-0 z-50 pt-safe dark:border-b dark:border-gray-800 border-b border-gray-200 md:border-b-0">
      {/* Daily progress bar */}
      <div className="h-1 dark:bg-gray-800 bg-gray-200 w-full">
        <div
          className="h-1 bg-indigo-500 transition-all duration-500"
          style={{ width: `${dailyProgress}%` }}
          title={`Dzienny postęp: ${dailyProgress}%`}
        />
      </div>
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-14 md:h-16 gap-2">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 shrink-0" aria-label="LinguaAI — strona główna">
            <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg dark:text-indigo-300 text-indigo-700 hidden sm:block">LinguaAI</span>
          </Link>

          {/* Right side: stats + dark mode + flash quick-add */}
          <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
            {quickTimer && (
              <Link to="/quickmode" className={`flex items-center gap-1.5 rounded-xl px-2.5 h-11 text-sm font-semibold tabular-nums ${quickTimer.active ? 'dark:bg-indigo-900/60 bg-indigo-100 dark:text-indigo-200 text-indigo-800' : 'dark:bg-gray-800 bg-gray-100 dark:text-gray-300 text-gray-700'}`} title="QuickMode timer">
                <Timer className="w-4 h-4" />
                <span>{fmtTimer(quickTimer.seconds)}</span>
              </Link>
            )}
            {userStats && (
              <div className="flex items-center gap-1.5 sm:gap-2">
                <div className="flex items-center gap-1.5 dark:bg-gray-800 bg-gray-100 rounded-xl px-2.5 h-11"
                  title="Dni z lekcją w tym tygodniu (cel 5 z 7)" data-testid="nav-week-days"
                  aria-label={`Dni z lekcją w tym tygodniu: ${weekDays?.days ?? 0} z ${weekDays?.goal ?? 5}`}>
                  <CalendarCheck className="w-4 h-4 dark:text-orange-300 text-orange-800" aria-hidden="true" />
                  <span className="text-sm font-semibold tabular-nums dark:text-orange-300 text-orange-800">
                    {weekDays?.days ?? 0}/{weekDays?.goal ?? 5}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 dark:bg-gray-800 bg-gray-100 rounded-xl px-2.5 h-11"
                  title="Łączne XP" aria-label={`Łączne XP: ${userStats.user?.total_xp || 0}`}>
                  <Star className="w-4 h-4 dark:text-yellow-300 text-yellow-800" aria-hidden="true" />
                  <span className="text-sm font-semibold tabular-nums dark:text-yellow-300 text-yellow-800">
                    {userStats.user?.total_xp || 0}
                  </span>
                </div>
                {userStats.user?.cefr_level && (
                  <div className="dark:bg-blue-900 bg-blue-100 dark:text-blue-200 text-blue-800 items-center px-2.5 py-0.5 rounded-full text-xs font-semibold hidden sm:flex">
                    {userStats.user.cefr_level}
                  </div>
                )}
              </div>
            )}

            {!userStats && !userId && (
              <Link to="/placement" className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium h-11 inline-flex items-center px-4 rounded-xl text-sm transition-colors">
                {t('nav.getStarted')}
              </Link>
            )}

            {/* Translator on phones (wider screens have the floating button) */}
            {onOpenTranslator && (
              <button
                onClick={onOpenTranslator}
                className={`sm:hidden ${iconBtn}`}
                title="Tłumacz" aria-label="Tłumacz" data-testid="nav-translator"
              >
                <Languages className="w-5 h-5 dark:text-indigo-300 text-indigo-700" />
              </button>
            )}

            {/* Dark mode toggle */}
            {onToggleDark && (
              <button
                onClick={onToggleDark}
                className={iconBtn}
                title={dark ? 'Tryb jasny' : 'Tryb ciemny'}
                aria-label={dark ? 'Włącz tryb jasny' : 'Włącz tryb ciemny'}
              >
                {dark ? <Sun className="w-5 h-5 text-yellow-300" /> : <Moon className="w-5 h-5 text-indigo-700" />}
              </button>
            )}

            {/* Flash quick-add — always visible on desktop */}
            {userId && (
              <div className="relative flex items-center gap-1.5">
                {/* Desktop: inline input */}
                <div className="hidden md:flex items-center gap-1.5 dark:bg-gray-800 bg-gray-100 dark:border dark:border-gray-700 border border-gray-300 rounded-xl px-2.5 h-11">
                  <BookmarkPlus className="w-4 h-4 dark:text-indigo-300 text-indigo-700 shrink-0" aria-hidden="true" />
                  <input
                    className="bg-transparent text-sm dark:text-gray-100 text-gray-800 dark:placeholder-gray-400 placeholder-gray-500 outline-none w-28"
                    placeholder="Dodaj fiszkę..."
                    aria-label="Dodaj fiszkę (AI uzupełni tłumaczenie)"
                    value={flashWord}
                    onChange={e => { setFlashWord(e.target.value); setFlashMsg('') }}
                    onKeyDown={e => e.key === 'Enter' && handleQuickFlash()}
                  />
                  {flashLoading && <Loader2 className="w-3 h-3 animate-spin text-indigo-400 shrink-0" />}
                  {flashMsg && <span className={`text-xs shrink-0 ${flashMsg.includes('Błąd') || flashMsg.includes('już istnieje') ? 'text-red-400' : 'text-emerald-400'}`}>{flashMsg.includes('Dodano') ? '✓' : '!'}</span>}
                </div>
                {/* Mobile: toggle button */}
                <button onClick={() => setFlashOpen(o => !o)} className="md:hidden w-11 h-11 rounded-xl bg-indigo-600 hover:bg-indigo-700 flex items-center justify-center" title="Dodaj fiszkę" aria-label="Dodaj fiszkę" aria-expanded={flashOpen}>
                  <BookmarkPlus className="w-5 h-5 text-white" />
                </button>
                {flashOpen && (
                  <div className="absolute right-0 top-12 dark:bg-gray-800 bg-white dark:border dark:border-gray-700 border border-gray-200 rounded-2xl shadow-2xl p-3 w-64 z-50 md:hidden">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold dark:text-indigo-300 text-indigo-700">Dodaj fiszkę (AI)</span>
                      <button className="w-9 h-9 -mr-1 rounded-lg flex items-center justify-center dark:hover:bg-gray-700 hover:bg-gray-100" aria-label="Zamknij" onClick={() => { setFlashOpen(false); setFlashMsg(''); setFlashWord('') }}><X className="w-4 h-4 dark:text-gray-300 text-gray-600" /></button>
                    </div>
                    <input className="dark:bg-gray-700 bg-gray-50 dark:border-gray-600 border border-gray-300 dark:text-gray-100 text-gray-800 rounded-xl px-3 py-2.5 w-full text-sm mb-2 outline-none focus:border-indigo-500" placeholder="Słowo..." aria-label="Słowo" value={flashWord} onChange={e => setFlashWord(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleQuickFlash()} autoFocus />
                    {flashMsg && <p className={`text-sm mb-2 ${flashMsg.includes('Błąd') || flashMsg.includes('już istnieje') ? 'dark:text-red-300 text-red-700' : 'dark:text-emerald-300 text-emerald-700'}`}>{flashMsg}</p>}
                    <button className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium flex items-center justify-center gap-1.5 disabled:opacity-50" onClick={handleQuickFlash} disabled={flashLoading || !flashWord.trim()}>
                      {flashLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookmarkPlus className="w-4 h-4" />}
                      Dodaj z AI
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>

    {/* md and up: all functions, grouped, with permanent text labels */}
    <nav aria-label="Wszystkie funkcje" data-testid="nav-desktop" className="hidden md:block dark:bg-gray-900 bg-white dark:border-b dark:border-gray-800 border-b border-gray-200 md:sticky md:top-[68px] md:z-40">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 pb-2 pt-1 border-t dark:border-gray-800/60 border-gray-100">
          {navGroups.map(group => (
            <div key={group.label} className="flex items-center flex-wrap gap-1">
              <span className="text-[11px] font-bold uppercase tracking-wider dark:text-gray-400 text-gray-600 mr-1 shrink-0">
                {group.label}
              </span>
              {group.items.map(({ to, label, icon: Icon, exact }) => (
                <Link
                  key={to}
                  to={to}
                  aria-current={isActive(to, exact) ? 'page' : undefined}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium transition-colors duration-200 shrink-0 ${
                    isActive(to, exact)
                      ? 'bg-indigo-600 text-white'
                      : 'dark:text-gray-300 text-gray-700 dark:hover:text-white hover:text-gray-900 dark:hover:bg-gray-800 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-4 h-4" aria-hidden="true" />
                  {label}
                </Link>
              ))}
            </div>
          ))}
        </div>
      </div>
    </nav>

    {/* Phones: bottom bar in the thumb zone (Hoober 2013: 49% one-handed use) */}
    <nav aria-label="Menu główne" data-testid="nav-bottom" className="md:hidden fixed bottom-0 inset-x-0 z-50 dark:bg-gray-900/95 bg-white/95 backdrop-blur dark:border-t dark:border-gray-800 border-t border-gray-200 pb-safe">
      <div className="grid grid-cols-5">
        {bottomItems.map(({ to, label, icon: Icon, exact }) => {
          const active = isActive(to, exact) && !allOpen
          return (
            <Link key={to} to={to} aria-current={active ? 'page' : undefined}
              className={`flex flex-col items-center justify-center gap-0.5 min-h-[56px] text-[12px] font-medium transition-colors ${
                active ? 'dark:text-indigo-300 text-indigo-700' : 'dark:text-gray-300 text-gray-600'}`}>
              <span className={`flex items-center justify-center w-14 h-7 rounded-full transition-colors ${active ? 'dark:bg-indigo-500/25 bg-indigo-100' : ''}`}>
                <Icon className="w-5 h-5" aria-hidden="true" />
              </span>
              {label}
            </Link>
          )
        })}
        <button type="button" onClick={() => setAllOpen(o => !o)} aria-expanded={allOpen} aria-controls="nav-all-sheet"
          data-testid="nav-all-button"
          className={`flex flex-col items-center justify-center gap-0.5 min-h-[56px] text-[12px] font-medium transition-colors ${
            allOpen ? 'dark:text-indigo-300 text-indigo-700' : 'dark:text-gray-300 text-gray-600'}`}>
          <span className={`flex items-center justify-center w-14 h-7 rounded-full ${allOpen ? 'dark:bg-indigo-500/25 bg-indigo-100' : ''}`}>
            {allOpen ? <X className="w-5 h-5" aria-hidden="true" /> : <LayoutList className="w-5 h-5" aria-hidden="true" />}
          </span>
          Wszystko
        </button>
      </div>
    </nav>

    {/* Phones: "Wszystko" — every function, grouped, each with its label */}
    {allOpen && (
      <div className="md:hidden fixed inset-0 z-40" data-testid="nav-all-sheet-wrap">
        <div className="absolute inset-0 bg-black/50" onClick={() => setAllOpen(false)} aria-hidden="true" />
        <div id="nav-all-sheet" role="dialog" aria-modal="true" aria-label="Wszystkie funkcje"
          className="absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-3xl dark:bg-gray-900 bg-white px-4 pt-3 pb-sheet shadow-2xl">
          <div className="mx-auto mb-3 h-1.5 w-10 rounded-full dark:bg-gray-700 bg-gray-300" aria-hidden="true" />
          {navGroups.map(group => (
            <section key={group.label} className="mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider dark:text-gray-400 text-gray-600 mb-2 px-1">{group.label}</h2>
              <div className="grid grid-cols-3 gap-2">
                {group.items.map(({ to, label, icon: Icon, exact }) => (
                  <Link key={to} to={to} aria-current={isActive(to, exact) ? 'page' : undefined}
                    className={`flex flex-col items-center justify-center gap-1.5 rounded-2xl min-h-[76px] px-1 text-center text-sm font-medium leading-tight transition-colors ${
                      isActive(to, exact)
                        ? 'bg-indigo-600 text-white'
                        : 'dark:bg-gray-800 bg-gray-100 dark:text-gray-100 text-gray-800 dark:hover:bg-gray-700 hover:bg-gray-200'}`}>
                    <Icon className="w-6 h-6" aria-hidden="true" />
                    {label}
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    )}
    </>
  )
}
