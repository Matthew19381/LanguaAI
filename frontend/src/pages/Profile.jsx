import { useState, useRef } from 'react'
import { Smartphone, Download, Upload, Copy, Check, Loader2 } from 'lucide-react'
import { getUserId, getLoginLink, exportProfile, importProfile } from '../api/client'
import { useLanguage } from '../hooks/useLanguage'
import PushToggle from '../components/PushToggle'

/**
 * Profile page — single-user tools:
 * 1. Phone pairing: a magic link that binds a new device to this account.
 * 2. Backup: download / restore the full learning profile as a JSON file.
 */
export default function Profile() {
  const userId = getUserId()
  const { t } = useLanguage()
  const [loginUrl, setLoginUrl] = useState('')
  const [copied, setCopied] = useState(false)
  const [busyLink, setBusyLink] = useState(false)
  const [busyExport, setBusyExport] = useState(false)
  const [busyImport, setBusyImport] = useState(false)
  const [message, setMessage] = useState('')
  const fileRef = useRef(null)

  const showLoginLink = async () => {
    setBusyLink(true)
    try {
      const { login_token } = await getLoginLink(userId)
      setLoginUrl(`${window.location.origin}/login-as?key=${login_token}`)
    } catch (e) {
      setMessage('Nie udało się pobrać linku: ' + e.message)
    } finally {
      setBusyLink(false)
    }
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(loginUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API unavailable (non-HTTPS) — user can select the text manually
    }
  }

  const downloadBackup = async () => {
    setBusyExport(true)
    try {
      const res = await exportProfile(userId)
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `linguaai_profile_${userId}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setMessage('Eksport nieudany: ' + e.message)
    } finally {
      setBusyExport(false)
    }
  }

  const restoreBackup = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBusyImport(true)
    setMessage('')
    try {
      const res = await importProfile(file)
      setMessage(`Profil przywrócony (użytkownik id=${res.data.user_id}). Odświeżam…`)
      setTimeout(() => window.location.reload(), 1500)
    } catch (err) {
      setMessage('Import nieudany: ' + (err.response?.data?.detail || err.message))
    } finally {
      setBusyImport(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold dark:text-white">Mój profil</h1>

      {/* Phone pairing */}
      <section className="rounded-xl border dark:border-gray-700 p-5 space-y-3 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold dark:text-white">Telefon / nowe urządzenie</h2>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Otwórz ten link na telefonie — urządzenie zostanie automatycznie zalogowane
          na Twoje konto (bez wpisywania czegokolwiek). Link działa tylko z adresem,
          pod którym widzisz tę stronę (przez tunel Cloudflare wklej adres tunelu).
        </p>
        {!loginUrl ? (
          <button
            onClick={showLoginLink}
            disabled={busyLink || !userId}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {busyLink && <Loader2 className="w-4 h-4 animate-spin" />}
            Pokaż link logowania
          </button>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                readOnly
                value={loginUrl}
                onFocus={(e) => e.target.select()}
                className="flex-1 text-xs p-2 rounded border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 font-mono"
              />
              <button
                onClick={copyLink}
                className="px-3 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 flex items-center gap-1"
              >
                {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-amber-600 dark:text-amber-400">
              ⚠️ Każdy, kto zna ten link, zaloguje się na Twoje konto. Nie udostępniaj go publicznie.
            </p>
          </div>
        )}
      </section>

      {/* Push notifications */}
      <PushToggle />

      {/* Backup */}
      <section className="rounded-xl border dark:border-gray-700 p-5 space-y-3 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-2">
          <Download className="w-5 h-5 text-green-500" />
          <h2 className="font-semibold dark:text-white">Kopia zapasowa postępów</h2>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Pełny profil: konto, lekcje, fiszki ze stanem powtórek (FSRS). Po awarii
          bazy wgraj plik z powrotem — postępy wracają bez przechodzenia onboardingu.
        </p>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={downloadBackup}
            disabled={busyExport || !userId}
            className="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
          >
            {busyExport ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Pobierz kopię (JSON)
          </button>
          <label className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 cursor-pointer flex items-center gap-2 dark:text-gray-100">
            {busyImport ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            Przywróć z pliku
            <input
              ref={fileRef}
              type="file"
              accept="application/json"
              onChange={restoreBackup}
              className="hidden"
            />
          </label>
        </div>
      </section>

      {message && (
        <p className="text-sm p-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200">
          {message}
        </p>
      )}
    </div>
  )
}
