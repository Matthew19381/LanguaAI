import { useState, useEffect, useCallback, useRef } from 'react'
import { Outlet } from 'react-router-dom'
import NavBar from './NavBar'
import NotificationManager from './NotificationManager'
import OfflineBanner from './OfflineBanner'
import { getUserId, getStats, askQuestion, translateWord, addFlashcard } from '../api/client'
import { useLanguage } from '../hooks/useLanguage'
import { useDarkMode } from '../hooks/useDarkMode'
import { useNavigate, useLocation } from 'react-router-dom'
import { Timer, Languages, X, ArrowRight, Sun, Moon } from 'lucide-react'

// Only these paths are auto-marked on visit (lesson + test require explicit completion)
const AUTO_VISIT_PATHS = ['/flashcards', '/conversation', '/quickmode', '/news', '/pronunciation']

function getTodayStr() {
  return new Date().toISOString().slice(0, 10)
}

function getDailyTabs() {
  try {
    const raw = localStorage.getItem('daily_tabs')
    if (!raw) return { date: getTodayStr(), tabs: [] }
    const parsed = JSON.parse(raw)
    if (parsed.date !== getTodayStr()) return { date: getTodayStr(), tabs: [] }
    return parsed
  } catch { return { date: getTodayStr(), tabs: [] } }
}

export default function Layout() {
  const [toasts, setToasts] = useState([])
  const userId = getUserId()
  const { t, targetLanguage } = useLanguage()
  const { dark, toggle: toggleDark } = useDarkMode()
  const navigate = useNavigate()
  const location = useLocation()
  const [timerDisplay, setTimerDisplay] = useState(null)

  // Daily progress state
  const [dailyTabs, setDailyTabs] = useState(() => getDailyTabs().tabs)

  const [timerSeconds, setTimerSeconds] = useState(null)

  useEffect(() => {
    const updateTimer = () => {
      const startTime = localStorage.getItem('quickmode_start')
      const duration = parseInt(localStorage.getItem('quickmode_duration') || '15') * 60
      if (!startTime) { setTimerDisplay(null); setTimerSeconds(null); return }
      const elapsed = Math.floor((Date.now() - parseInt(startTime)) / 1000)
      const remaining = duration - elapsed
      if (remaining <= 0) {
        localStorage.removeItem('quickmode_start')
        setTimerDisplay(null)
        setTimerSeconds(null)
      } else {
        const m = Math.floor(remaining / 60)
        const s = remaining % 60
        setTimerDisplay(`${m}:${s.toString().padStart(2, '0')}`)
        setTimerSeconds(remaining)
      }
    }
    updateTimer()
    const interval = setInterval(updateTimer, 1000)

    // Handle tab visibility changes - immediately resync when user returns
    const handleVisibilityChange = () => {
      if (!document.hidden) updateTimer()
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  // Poll for new achievements — on route change AND on a retry interval
  const checkNewAchievements = useCallback(async () => {
    if (!userId) return
    try {
      const data = await getStats(userId)
      const newAchs = data?.new_achievements || []
      if (newAchs.length > 0) {
        setToasts(prev => [
          ...prev,
          ...newAchs.map((a, i) => ({ ...a, id: Date.now() + i }))
        ])
      }
    } catch (_) {}
  }, [userId])

  // Check on route change
  useEffect(() => {
    checkNewAchievements()
  }, [checkNewAchievements, location.pathname])

  // Stale userId (user deleted from DB): client.js clears localStorage and
  // fires 'user-not-found' → send the user to onboarding instead of looping 404s.
  useEffect(() => {
    const onUserNotFound = () => {
      window.location.href = '/placement'
    }
    window.addEventListener('user-not-found', onUserNotFound)
    return () => window.removeEventListener('user-not-found', onUserNotFound)
  }, [])

  // Retry polling every 30 seconds to catch achievements missed by route changes
  useEffect(() => {
    if (!userId) return
    const interval = setInterval(checkNewAchievements, 30000)
    return () => clearInterval(interval)
  }, [checkNewAchievements, userId])

  // Track daily tab visits
  useEffect(() => {
    const path = location.pathname
    const isAutoPath = AUTO_VISIT_PATHS.some(p => path.startsWith(p))
    if (isAutoPath) {
      const key = path.replace('/', '').split('/')[0]
      const stored = getDailyTabs()
      if (!stored.tabs.includes(key)) {
        const updated = { date: getTodayStr(), tabs: [...stored.tabs, key] }
        localStorage.setItem('daily_tabs', JSON.stringify(updated))
        setDailyTabs(updated.tabs)
      }
    }
    // Reload daily tabs on every navigation to catch lesson/test completions
    setDailyTabs(getDailyTabs().tabs)
  }, [location.pathname])

  const removeToast = (id) => setToasts(prev => prev.filter(t => t.id !== id))

  return (
    <div className="min-h-screen dark:bg-gray-950 bg-gray-50 transition-colors duration-200">
      <OfflineBanner />
      <NavBar dailyTabs={dailyTabs} dark={dark} onToggleDark={toggleDark} />
      <NotificationManager />
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Timer Badge */}
      {timerDisplay && (
        <button
          onClick={() => navigate('/quickmode')}
          className={`fixed bottom-6 right-4 z-50 flex items-center gap-2 px-5 py-3 rounded-xl shadow-lg transition-colors ${
            timerSeconds <= 5 ? 'bg-red-700 hover:bg-red-600 animate-blink' :
            timerSeconds < 60 ? 'bg-red-700 hover:bg-red-600' :
            timerSeconds < 300 ? 'bg-yellow-600 hover:bg-yellow-500' :
            'bg-emerald-700 hover:bg-emerald-600'
          } text-white`}
        >
          <Timer className="w-8 h-8" />
          <span className="font-mono font-bold text-4xl">{timerDisplay}</span>
        </button>
      )}

      {/* Translation Widget */}
      <TranslatorWidget userId={userId} targetLanguage={targetLanguage} />

      {/* Achievement toasts */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-xs">
        {toasts.map((toast) => (
          <AchievementToast
            key={toast.id}
            toast={toast}
            onClose={() => removeToast(toast.id)}
            label={t('achievement.unlocked')}
          />
        ))}
      </div>
    </div>
  )
}

function TranslatorWidget({ userId, targetLanguage }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeMode, setActiveMode] = useState(null) // 'translate' | 'explain'
  const [flashAdded, setFlashAdded] = useState(false)
  // 'to_native' = target lang → Polish, 'to_target' = Polish → target lang
  const [dir, setDir] = useState('to_native')

  const targetShort = targetLanguage || 'EN'
  const fromLang = dir === 'to_native' ? targetLanguage || 'English' : 'Polish'
  const toLang   = dir === 'to_native' ? 'Polish' : targetLanguage || 'English'
  const dirLabel = dir === 'to_native' ? `${targetShort} → PL` : `PL → ${targetShort}`
  const flipDir  = () => { setDir(d => d === 'to_native' ? 'to_target' : 'to_native'); setResult(''); setFlashAdded(false) }

  const handleAction = async (actionMode) => {
    if (!text.trim() || !userId) return
    setLoading(true)
    setActiveMode(actionMode)
    setResult('')
    setFlashAdded(false)
    try {
      const t = text.trim()
      if (actionMode === 'explain') {
        const prompt = `Wyjaśnij po polsku znaczenie i użycie wyrazu/frazy: "${t}" (język: ${fromLang}). Napisz 2-3 zdania: znaczenie, kiedy się używa, przykład.`
        const res = await askQuestion(prompt, userId)
        setResult(res.answer || '')
      } else {
        const res = await translateWord(t, fromLang, toLang, userId)
        setResult(res.translation || '')
      }
    } catch {
      setResult('Błąd.')
    } finally {
      setLoading(false)
      setActiveMode(null)
    }
  }

  const handleAddFlash = async () => {
    if (!result || !text.trim() || !userId) return
    try {
      // to_native: text=target lang, result=Polish → word=text, translation=result
      // to_target: text=Polish, result=target lang → word=result, translation=text
      const isToNative = dir === 'to_native'
      await addFlashcard(userId, {
        word: isToNative ? text.trim() : result.trim(),
        translation: isToNative ? result.trim() : text.trim()
      })
      setFlashAdded(true)
    } catch {}
  }

  const close = () => { setOpen(false); setResult(''); setText(''); setFlashAdded(false) }

  return (
    <div className="fixed bottom-6 left-4 z-40">
      {open ? (
        <div className="dark:bg-gray-900 bg-white dark:border dark:border-gray-700 border border-gray-200 rounded-xl shadow-2xl p-3 w-72">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Languages className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-semibold dark:text-gray-200 text-gray-800">Tłumacz</span>
            </div>
            <button onClick={close}><X className="w-4 h-4 dark:text-gray-500 text-gray-400 dark:hover:text-gray-300 hover:text-gray-600" /></button>
          </div>
          {/* Direction toggle */}
          <button
            onClick={flipDir}
            className="w-full mb-2 py-1 rounded-lg dark:bg-gray-800 bg-gray-100 dark:hover:bg-gray-700 hover:bg-gray-200 dark:border dark:border-gray-700 border border-gray-300 text-xs text-indigo-500 font-medium flex items-center justify-center gap-1.5 transition-colors"
          >
            <ArrowRight className="w-3 h-3" />
            {dirLabel} — kliknij aby odwrócić
          </button>
          <textarea
            className="w-full dark:bg-gray-800 bg-gray-50 dark:border dark:border-gray-700 border border-gray-300 rounded-lg p-2 text-sm dark:text-gray-200 text-gray-800 resize-none h-16 focus:outline-none focus:border-indigo-500 dark:placeholder-gray-500 placeholder-gray-400"
            placeholder={dir === 'to_native' ? `Wpisz po ${targetShort}...` : 'Wpisz po polsku...'}
            value={text}
            onChange={e => { setText(e.target.value); setResult(''); setFlashAdded(false) }}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAction('translate') } }}
            autoFocus
          />
          <div className="flex gap-1.5 mt-2">
            <button
              onClick={() => handleAction('translate')}
              disabled={loading || !text.trim()}
              className="flex-1 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5"
            >
              {loading && activeMode === 'translate' ? '...' : 'Tłumacz'}
            </button>
            <button
              onClick={() => handleAction('explain')}
              disabled={loading || !text.trim()}
              className="flex-1 py-1.5 rounded-lg dark:bg-gray-700 bg-gray-200 dark:hover:bg-gray-600 hover:bg-gray-300 dark:text-gray-200 text-gray-700 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {loading && activeMode === 'explain' ? '...' : 'Wytłumacz'}
            </button>
          </div>
          {result && (
            <div className="mt-2 p-2.5 dark:bg-gray-800 bg-indigo-50 rounded-lg dark:border dark:border-indigo-700/30 border border-indigo-200">
              <p className="text-sm dark:text-emerald-300 text-emerald-700 leading-relaxed">{result}</p>
              <button
                onClick={handleAddFlash}
                disabled={flashAdded}
                className="mt-1.5 text-xs text-indigo-500 hover:text-indigo-400 disabled:text-emerald-500 transition-colors"
              >
                {flashAdded ? '✓ Dodano do fiszek' : '+ Dodaj do fiszek'}
              </button>
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 dark:bg-gray-800 bg-white hover:bg-indigo-600 dark:border dark:border-gray-700 border border-gray-200 dark:hover:border-indigo-600 dark:text-gray-300 text-gray-600 hover:text-white px-3 py-2 rounded-xl shadow-lg transition-all"
          title="Tłumacz"
        >
          <Languages className="w-5 h-5" />
          <span className="text-sm font-medium">Tłumacz</span>
        </button>
      )}
    </div>
  )
}

function AchievementToast({ toast, onClose, label }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className="dark:bg-gray-800 bg-white dark:border-yellow-600/50 border border-yellow-400 rounded-xl px-4 py-3 shadow-2xl flex items-center gap-3 animate-fade-in">
      <span className="text-2xl">{toast.icon}</span>
      <div className="flex-1">
        <p className="text-yellow-500 font-semibold text-sm">{label}</p>
        <p className="dark:text-white text-gray-900 text-sm">{toast.title}</p>
        <p className="dark:text-gray-400 text-gray-500 text-xs">{toast.description}</p>
      </div>
      <button onClick={onClose} className="dark:text-gray-500 text-gray-400 dark:hover:text-gray-300 hover:text-gray-600 text-lg leading-none">×</button>
    </div>
  )
}
