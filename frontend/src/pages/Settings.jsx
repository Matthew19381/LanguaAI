import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Globe, Settings as SettingsIcon } from 'lucide-react'
import { getUserId, getStats, getLanguageProfiles, updateUserLanguage } from '../api/client'
import { NotificationSettings } from '../components/NotificationManager'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'

const LANGUAGES = ['German', 'English', 'Spanish', 'Russian', 'Chinese']

const LANG_FLAGS = {
  German: '🇩🇪',
  English: '🇬🇧',
  Spanish: '🇪🇸',
  Russian: '🇷🇺',
  Chinese: '🇨🇳',
}

const LANG_NAMES_PL = {
  German: 'Niemiecki',
  English: 'Angielski',
  Spanish: 'Hiszpański',
  Russian: 'Rosyjski',
  Chinese: 'Chiński',
}

export default function Settings() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [languageProfiles, setLanguageProfiles] = useState(null)
  const [changingLanguage, setChangingLanguage] = useState(false)
  const [languageMsg, setLanguageMsg] = useState('')
  const navigate = useNavigate()
  const userId = getUserId()
  const { lang, setLang, t, targetLanguage } = useLanguage()

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    getStats(userId)
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
    getLanguageProfiles(userId)
      .then(setLanguageProfiles)
      .catch(() => {})
  }, [userId])

  const handleChangeLanguage = async (newLanguage) => {
    if (!userId || newLanguage === stats?.user?.target_language) return
    setChangingLanguage(true)
    try {
      const result = await updateUserLanguage(userId, newLanguage)
      // Clear cached data for old language
      localStorage.removeItem('tips_date')
      localStorage.removeItem('tips_data')
      localStorage.removeItem('daily_tabs')
      // Clear lesson + test cache for all languages
      Object.keys(localStorage)
        .filter(k => k.startsWith('lesson_cache_') || k.startsWith('test_cache_'))
        .forEach(k => localStorage.removeItem(k))
      localStorage.setItem('userLanguage', newLanguage)
      if (result.needs_placement) {
        navigate(`/placement?language=${encodeURIComponent(newLanguage)}&userId=${userId}`)
      } else {
        window.location.reload()
      }
    } catch (e) {
      setLanguageMsg('Błąd: ' + e.message)
      setChangingLanguage(false)
    }
  }

  const handleRegenerateLesson = async () => {
    if (!userId) return
    try {
      await fetch(`/api/lessons/next/${userId}`, { method: 'POST' })
      window.location.href = '/lesson'
    } catch (e) {
      alert('Błąd: ' + e.message)
    }
  }

  if (loading) return <PageLoader text="Ładowanie ustawień..." />
  if (!stats) return null

  const { user } = stats

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="w-7 h-7 text-indigo-400" />
        <h1 className="text-2xl font-bold">Ustawienia</h1>
      </div>

      {/* Settings */}
      <div className="card mb-6">
        <h2 className="section-title flex items-center gap-2">
          <Globe className="w-5 h-5 text-indigo-400" />
          {t('stats.settings')}
        </h2>

        {/* UI Language Toggle */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-300 text-sm">{t('stats.uiLanguage')}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setLang('pl')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                lang === 'pl' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'
              }`}
            >
              {t('stats.polishMode')}
            </button>
            {targetLanguage === 'English' ? (
              <button
                onClick={() => setLang('hardcore')}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  lang === 'hardcore' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'
                }`}
              >
                Hardcore (EN)
              </button>
            ) : (
              <span className="px-4 py-1.5 rounded-lg text-sm bg-gray-800/50 text-gray-600" title="Dostępne tylko dla języka angielskiego">
                Hardcore (tylko EN)
              </span>
            )}
          </div>
        </div>

        {/* Target Language Change */}
        <div className="mb-4 mt-4">
          <span className="text-gray-300 text-sm block mb-1">Zmień język nauki</span>
          <span className="text-gray-500 text-xs mb-3 block">Progres dla każdego języka jest zachowywany oddzielnie</span>
          <div className="grid grid-cols-5 gap-2">
            {LANGUAGES.map(lng => {
              const profile = languageProfiles?.languages?.find(p => p.language === lng)
              const isActive = user?.target_language === lng
              const cefr = profile?.cefr_level
              const started = profile?.started
              return (
                <button
                  key={lng}
                  onClick={() => handleChangeLanguage(lng)}
                  disabled={changingLanguage || isActive}
                  className={`flex flex-col items-center gap-1 p-2 rounded-lg border text-center transition-all ${
                    isActive
                      ? 'bg-indigo-700/40 border-indigo-500 text-white'
                      : started
                      ? 'bg-gray-800 border-gray-600 text-gray-300 hover:border-indigo-500'
                      : 'bg-gray-900/50 border-gray-800 text-gray-500 hover:border-gray-600'
                  } disabled:cursor-default`}
                >
                  <span className="text-xl">{LANG_FLAGS[lng]}</span>
                  <span className="text-xs font-medium leading-tight">{LANG_NAMES_PL[lng] || lng}</span>
                  {cefr ? (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      isActive ? 'bg-indigo-500 text-white' : 'bg-gray-700 text-gray-300'
                    }`}>{cefr}</span>
                  ) : (
                    <span className="text-[10px] text-gray-600">—</span>
                  )}
                  {profile?.lessons_completed > 0 && (
                    <span className="text-[10px] text-gray-500">{profile.lessons_completed} lekcji</span>
                  )}
                </button>
              )
            })}
          </div>
          {changingLanguage && <p className="text-xs text-indigo-400 mt-2">Zmienianie języka...</p>}
          {languageMsg && <p className="text-sm text-indigo-300 mt-2">{languageMsg}</p>}
        </div>

        <button
          onClick={handleRegenerateLesson}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-red-900/30 hover:border-red-700/30 border border-transparent text-gray-300 hover:text-red-300 text-sm transition-colors mt-2"
        >
          Wygeneruj następną lekcję
        </button>
      </div>

      {/* Notification Settings */}
      <NotificationSettings />
    </div>
  )
}
