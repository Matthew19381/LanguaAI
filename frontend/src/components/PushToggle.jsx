import { useState, useEffect } from 'react'
import { Bell, BellOff, Loader2, Send } from 'lucide-react'
import { getUserId, getVapidPublicKey, sendTestPush } from '../api/client'
import { pushSupported, isSubscribed, enablePush, disablePush } from '../utils/push'

const ERRORS = {
  unsupported: 'Ta przeglądarka nie obsługuje powiadomień push.',
  disabled: 'Powiadomienia nie są skonfigurowane na serwerze (brak kluczy VAPID).',
  denied: 'Odmówiono zgody na powiadomienia. Zmień to w ustawieniach przeglądarki.',
}

/**
 * Enable / disable browser push notifications for this device, plus a test send.
 * Renders nothing actionable until it knows the browser supports push AND the
 * server has VAPID keys configured — otherwise it explains why.
 */
export default function PushToggle() {
  const userId = getUserId()
  const [available, setAvailable] = useState(null) // null = still checking
  const [on, setOn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!pushSupported()) {
        if (!cancelled) setAvailable(false)
        return
      }
      try {
        const { enabled } = await getVapidPublicKey()
        if (cancelled) return
        setAvailable(enabled)
        if (enabled) setOn(await isSubscribed())
      } catch {
        if (!cancelled) setAvailable(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  const toggle = async () => {
    setBusy(true)
    setMsg('')
    try {
      if (on) {
        await disablePush()
        setOn(false)
        setMsg('Powiadomienia wyłączone na tym urządzeniu.')
      } else {
        await enablePush(userId)
        setOn(true)
        setMsg('Powiadomienia włączone. 🔔')
      }
    } catch (e) {
      setMsg(ERRORS[e.message] || ('Nie udało się: ' + e.message))
    } finally {
      setBusy(false)
    }
  }

  const test = async () => {
    setBusy(true)
    setMsg('')
    try {
      await sendTestPush(userId)
      setMsg('Wysłano testowe powiadomienie — sprawdź ekran.')
    } catch (e) {
      setMsg('Test nieudany: ' + (e.response?.data?.detail || e.message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="rounded-xl border dark:border-gray-700 p-5 space-y-3 bg-white dark:bg-gray-900">
      <div className="flex items-center gap-2">
        <Bell className="w-5 h-5 text-indigo-500" />
        <h2 className="font-semibold dark:text-white">Powiadomienia o powtórkach</h2>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-300">
        Przypomnienia na telefon, gdy fiszki czekają na powtórkę — nawet przy
        zamkniętej aplikacji. Włącz osobno na każdym urządzeniu.
      </p>

      {available === null ? (
        <p className="text-sm text-gray-400 flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Sprawdzam…
        </p>
      ) : available === false ? (
        <p className="text-sm text-amber-600 dark:text-amber-400">
          {pushSupported() ? ERRORS.disabled : ERRORS.unsupported}
        </p>
      ) : (
        <div className="flex gap-3 flex-wrap items-center">
          <button
            onClick={toggle}
            disabled={busy || !userId}
            className={`px-4 py-2 rounded-lg text-white disabled:opacity-50 flex items-center gap-2 ${
              on ? 'bg-gray-600 hover:bg-gray-700' : 'bg-indigo-600 hover:bg-indigo-700'
            }`}
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : on ? <BellOff className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
            {on ? 'Wyłącz na tym urządzeniu' : 'Włącz powiadomienia'}
          </button>
          {on && (
            <button
              onClick={test}
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center gap-2 dark:text-gray-100"
            >
              <Send className="w-4 h-4" /> Wyślij test
            </button>
          )}
        </div>
      )}

      {msg && <p className="text-sm text-gray-600 dark:text-gray-300">{msg}</p>}
    </section>
  )
}
