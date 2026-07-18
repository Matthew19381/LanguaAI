import { useState, useEffect } from 'react'
import { Lock, Loader2 } from 'lucide-react'
import { getAuthStatus, unlockApp } from '../api/client'
import { useLanguage } from '../hooks/useLanguage'

/**
 * Shown when the backend is running behind a shared-secret gate and this device
 * has not been unlocked yet.
 *
 * Only relevant when the app is exposed beyond localhost (tunnel, cloud). With
 * no APP_ACCESS_TOKEN configured the gate is off and this never renders.
 */
export default function UnlockGate({ children }) {
  const [locked, setLocked] = useState(false)
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { t } = useLanguage()

  useEffect(() => {
    // Any 401 anywhere in the app flips us into the locked state
    const onLocked = () => setLocked(true)
    window.addEventListener('app-locked', onLocked)

    getAuthStatus()
      .then(s => setLocked(s.gate_enabled && !s.unlocked))
      .catch(() => {}) // offline or gate unreachable — let the app render

    return () => window.removeEventListener('app-locked', onLocked)
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    if (!token.trim()) return
    setBusy(true)
    setError('')
    try {
      await unlockApp(token.trim())
      // Reload so every screen refetches with the cookie in place
      window.location.reload()
    } catch {
      setError(t('unlock.wrong'))
      setBusy(false)
    }
  }

  if (!locked) return children

  return (
    <div className="min-h-screen flex items-center justify-center p-4 dark:bg-gray-950 bg-gray-50">
      <form onSubmit={submit} className="card w-full max-w-sm text-center">
        <Lock className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
        <h1 className="text-xl font-bold mb-1">{t('unlock.title')}</h1>
        <p className="text-gray-400 text-sm mb-4">{t('unlock.hint')}</p>
        <input
          type="password"
          value={token}
          onChange={e => setToken(e.target.value)}
          autoFocus
          placeholder={t('unlock.placeholder')}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-gray-100 focus:outline-none focus:border-indigo-600"
        />
        {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
        <button
          type="submit"
          disabled={!token.trim() || busy}
          className="btn-primary w-full mt-3 flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {busy && <Loader2 className="w-4 h-4 animate-spin" />}
          {t('unlock.submit')}
        </button>
      </form>
    </div>
  )
}
