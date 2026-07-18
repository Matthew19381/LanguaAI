import { useState, useEffect } from 'react'
import { WifiOff } from 'lucide-react'
import { useLanguage } from '../hooks/useLanguage'

/**
 * Tells the user when they are offline.
 *
 * The service worker serves cached lessons, flashcards and exercises offline,
 * but anything that writes (answering an exercise, completing a lesson,
 * generating new content) needs the network — so the message says so rather
 * than implying the app is fully usable.
 */
export default function OfflineBanner() {
  const [offline, setOffline] = useState(() => typeof navigator !== 'undefined' && !navigator.onLine)
  const { t } = useLanguage()

  useEffect(() => {
    const goOffline = () => setOffline(true)
    const goOnline = () => setOffline(false)
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [])

  if (!offline) return null

  return (
    <div
      role="status"
      className="sticky top-0 z-50 flex items-center justify-center gap-2 bg-amber-900/80 text-amber-100 text-xs px-3 py-2 backdrop-blur"
    >
      <WifiOff className="w-4 h-4 shrink-0" />
      <span>{t('offline.banner')}</span>
    </div>
  )
}
