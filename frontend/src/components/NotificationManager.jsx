import { useEffect, useRef } from 'react'
import { getUserId } from '../api/client'

const STORAGE_KEY = 'notif_time'
const DEFAULT_HOUR = 20 // 8 PM

function getNotifHour() {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored ? parseInt(stored) : DEFAULT_HOUR
}

function msUntilNextNotif(hour) {
  const now = new Date()
  const target = new Date()
  target.setHours(hour, 0, 0, 0)
  if (target <= now) {
    target.setDate(target.getDate() + 1)
  }
  return target - now
}

export default function NotificationManager() {
  const timerRef = useRef(null)
  const userId = getUserId()

  useEffect(() => {
    if (!userId) return
    if (!('Notification' in window)) return

    if (Notification.permission === 'default') {
      Notification.requestPermission()
    }

    scheduleNotif()
    return () => clearTimeout(timerRef.current)
  }, [userId])

  function scheduleNotif() {
    const hour = getNotifHour()
    const delay = msUntilNextNotif(hour)

    timerRef.current = setTimeout(() => {
      sendNotif()
      scheduleNotif() // reschedule for next day
    }, delay)
  }

  function sendNotif() {
    if (Notification.permission !== 'granted') return
    const messages = [
      'Czas na dzisiejszą lekcję! 📚',
      'Nie przerywaj serii — poćwicz dziś 🔥',
      'Twój język czeka na Ciebie! 🌍',
      '15 minut ćwiczeń podtrzyma Twoją serię! ⚡',
    ]
    const msg = messages[Math.floor(Math.random() * messages.length)]
    new Notification('LinguaAI', {
      body: msg,
      icon: '/favicon.ico',
    })
  }

  return null // no UI, runs in background
}

export function NotificationSettings() {
  const hour = getNotifHour()

  function handleChange(e) {
    localStorage.setItem(STORAGE_KEY, e.target.value)
  }

  async function requestPermission() {
    if ('Notification' in window) {
      const result = await Notification.requestPermission()
      if (result === 'granted') {
        alert('Powiadomienia włączone!')
      } else {
        alert('Powiadomienia zablokowane. Włącz je w ustawieniach przeglądarki.')
      }
    }
  }

  const permissionStatus = 'Notification' in window ? Notification.permission : 'unsupported'

  return (
    <div className="card mb-6">
      <h2 className="section-title flex items-center gap-2 mb-4">
        <span>🔔</span>
        Codzienne przypomnienie
      </h2>
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <label className="text-gray-400 text-sm w-32">Godzina:</label>
          <select
            defaultValue={hour}
            onChange={handleChange}
            className="input-field w-32 text-sm"
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>
                {i.toString().padStart(2, '0')}:00
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-gray-400 text-sm w-32">Status:</span>
          <span className={`text-sm font-medium ${
            permissionStatus === 'granted' ? 'text-emerald-400' :
            permissionStatus === 'denied' ? 'text-red-400' : 'text-yellow-400'
          }`}>
            {permissionStatus === 'granted' ? 'Włączone' :
             permissionStatus === 'denied' ? 'Zablokowane' :
             permissionStatus === 'unsupported' ? 'Nieobsługiwane' : 'Nie ustawiono'}
          </span>
          {permissionStatus !== 'granted' && permissionStatus !== 'unsupported' && (
            <button
              onClick={requestPermission}
              className="btn-primary text-xs py-1 px-3"
            >
              Włącz
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
