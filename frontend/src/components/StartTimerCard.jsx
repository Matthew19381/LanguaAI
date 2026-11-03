import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Timer, Play, Square } from 'lucide-react'

// Start the study timer straight from the home page (3.11.2026). It writes the same
// localStorage keys as /quickmode, so the header badge and the Timer page show the
// same countdown.
const KEY_START = 'quickmode_start'
const KEY_DURATION = 'quickmode_duration'
const KEY_PAUSED = 'quickmode_paused_remaining'
const CHOICES = [5, 10, 15, 20, 30]

function readRemaining() {
  try {
    const start = localStorage.getItem(KEY_START)
    if (!start) return null
    const duration = parseInt(localStorage.getItem(KEY_DURATION) || '15') * 60
    const left = duration - Math.floor((Date.now() - parseInt(start)) / 1000)
    return left > 0 ? left : null
  } catch { return null }
}

export default function StartTimerCard() {
  const [minutes, setMinutes] = useState(() => {
    try { return parseInt(localStorage.getItem(KEY_DURATION) || '15') || 15 } catch { return 15 }
  })
  const [remaining, setRemaining] = useState(readRemaining)

  useEffect(() => {
    const id = setInterval(() => setRemaining(readRemaining()), 1000)
    return () => clearInterval(id)
  }, [])

  const start = () => {
    try {
      localStorage.setItem(KEY_DURATION, String(minutes))
      localStorage.setItem(KEY_START, String(Date.now()))
      localStorage.removeItem(KEY_PAUSED)
    } catch { /* storage blocked: nothing to start */ }
    setRemaining(readRemaining())
  }
  const stop = () => {
    try {
      localStorage.removeItem(KEY_START)
      localStorage.removeItem(KEY_PAUSED)
    } catch { /* ignore */ }
    setRemaining(null)
  }

  const mm = remaining != null ? `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}` : null

  return (
    <div className="card !p-3 sm:!p-4 mb-4" data-testid="start-timer">
      <div className="flex items-center gap-3">
        <span className="flex items-center justify-center w-11 h-11 rounded-xl shrink-0 dark:bg-emerald-900/50 bg-emerald-100 dark:text-emerald-300 text-emerald-700" aria-hidden="true">
          <Timer className="w-6 h-6" />
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold">Timer nauki</p>
          {mm ? (
            <p className="text-sm dark:text-emerald-300 text-emerald-700 tabular-nums">Trwa: zostało {mm}</p>
          ) : (
            <div className="flex flex-wrap gap-1 mt-1" role="group" aria-label="Minuty">
              {CHOICES.map(m => (
                <button key={m} type="button" onClick={() => setMinutes(m)} aria-pressed={minutes === m}
                  className={`px-2.5 h-9 rounded-lg text-sm ${minutes === m ? 'bg-emerald-600 text-white' : 'dark:bg-gray-800 bg-gray-100 dark:text-gray-200 text-gray-800'}`}>
                  {m} min
                </button>
              ))}
            </div>
          )}
        </div>
        {mm ? (
          <button type="button" onClick={stop} className="btn-secondary h-11 px-3 flex items-center gap-1" aria-label="Zatrzymaj timer">
            <Square className="w-4 h-4" /> Stop
          </button>
        ) : (
          <button type="button" onClick={start} className="btn-success h-11 px-3 flex items-center gap-1" aria-label={`Start timera ${minutes} min`}>
            <Play className="w-4 h-4" /> Start
          </button>
        )}
      </div>
      <Link to="/quickmode" className="block text-xs mt-2 dark:text-indigo-300 text-indigo-700 underline">Plan na te minuty i timer z pauzą</Link>
    </div>
  )
}
