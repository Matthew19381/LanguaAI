import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Youtube, Search, RefreshCw, ExternalLink, Play, X, BookOpen, CheckCircle, Heart, Plus, Users } from 'lucide-react'
import { getUserId, searchYouTube } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'

const FAVS_KEY = 'video_favorites'
const CREATORS_KEY = 'video_favorite_creators'

function loadFavorites() {
  try { return JSON.parse(localStorage.getItem(FAVS_KEY) || '[]') } catch { return [] }
}
function saveFavorites(favs) {
  localStorage.setItem(FAVS_KEY, JSON.stringify(favs))
}
function loadCreators() {
  try { return JSON.parse(localStorage.getItem(CREATORS_KEY) || '[]') } catch { return [] }
}
function saveCreators(creators) {
  localStorage.setItem(CREATORS_KEY, JSON.stringify(creators))
}

export default function Videos() {
  const navigate = useNavigate()
  const userId = getUserId()
  const { t, targetLanguage } = useLanguage()

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [activeVideoId, setActiveVideoId] = useState(null)
  const [activityDone, setActivityDone] = useState(false)
  const [favorites, setFavorites] = useState(loadFavorites)
  const [showFavs, setShowFavs] = useState(false)
  const [creators, setCreators] = useState(loadCreators)
  const [creatorInput, setCreatorInput] = useState('')
  const [includePolish, setIncludePolish] = useState(false) // Polish explanations toggle

  const toggleFavorite = (video) => {
    setFavorites(prev => {
      const exists = prev.some(f => f.video_id === video.video_id)
      const next = exists
        ? prev.filter(f => f.video_id !== video.video_id)
        : [...prev, { video_id: video.video_id, title: video.title, channel: video.channel, thumbnail: video.thumbnail, url: video.url }]
      saveFavorites(next)
      return next
    })
  }
  const isFav = (video_id) => favorites.some(f => f.video_id === video_id)

  const addCreator = () => {
    const name = creatorInput.trim()
    if (!name || creators.includes(name)) return
    const next = [...creators, name]
    setCreators(next)
    saveCreators(next)
    setCreatorInput('')
  }

  const removeCreator = (name) => {
    const next = creators.filter(c => c !== name)
    setCreators(next)
    saveCreators(next)
  }

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    loadSuggested()
  }, [userId])

  const loadSuggested = async () => {
    setLoading(true)
    setError('')
    setActiveVideoId(null)
    setQuery('')
    try {
      const result = await searchYouTube(userId, '', includePolish)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (e) => {
    e?.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setError('')
    setActiveVideoId(null)
    try {
      const result = await searchYouTube(userId, query.trim(), includePolish)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setSearching(false)
    }
  }

  const handleSuggestedClick = async (sq) => {
    setQuery(sq)
    setSearching(true)
    setError('')
    setActiveVideoId(null)
    try {
      const result = await searchYouTube(userId, sq, includePolish)
      setData({ ...result, suggested: false })
    } catch (e) {
      setError(e.message)
    } finally {
      setSearching(false)
    }
  }

  const markTabComplete = (tabKey) => {
    try {
      const today = new Date().toISOString().slice(0, 10)
      const raw = localStorage.getItem('daily_tabs')
      const stored = raw ? JSON.parse(raw) : { date: today, tabs: [] }
      const current = stored.date === today ? stored : { date: today, tabs: [] }
      if (!current.tabs.includes(tabKey)) {
        current.tabs.push(tabKey)
        localStorage.setItem('daily_tabs', JSON.stringify(current))
      }
    } catch {}
  }

  const handleMarkDone = async () => {
    markTabComplete('videos')
    setActivityDone(true)
  }

  if (loading) return <PageLoader text="Szukam filmów dopasowanych do Twojej lekcji..." />

  const videos = data?.videos || []
  const topicVideos = videos.filter(v => v.is_lesson_related)
  const generalVideos = videos.filter(v => !v.is_lesson_related)
  const isCustomSearch = data && !data.suggested

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Youtube className="w-7 h-7 text-red-400" />
          <div>
            <h1 className="text-2xl font-bold">Filmy YouTube</h1>
            <p className="text-gray-400 text-sm">
              {data?.language} · poziom {data?.cefr_level}
              {data?.lesson_topic && !isCustomSearch && (
                <span className="ml-2 text-indigo-400">· temat: {data.lesson_topic}</span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFavs(s => !s)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors ${showFavs ? 'bg-red-700/40 text-red-300 border border-red-700/40' : 'bg-gray-800 hover:bg-gray-700 text-gray-300'}`}
          >
            <Heart className={`w-4 h-4 ${showFavs ? 'fill-red-400 text-red-400' : ''}`} />
            Ulubione {favorites.length > 0 && `(${favorites.length})`}
          </button>
          <button
            onClick={loadSuggested}
            disabled={loading || searching}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${(loading || searching) ? 'animate-spin' : ''}`} />
            Odśwież
          </button>
        </div>
      </div>

      {!activityDone ? (
        <button
          onClick={handleMarkDone}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700/30 hover:bg-emerald-700/50 border border-emerald-700/40 text-emerald-300 text-sm font-medium transition-colors mb-4"
        >
          <CheckCircle className="w-4 h-4" />
          Oznacz Filmy jako ukończone (+10 XP)
        </button>
      ) : (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-900/30 border border-emerald-700/40 text-emerald-400 text-sm font-medium mb-4">
          <CheckCircle className="w-4 h-4" />
          Filmy ukończone dziś ✓
        </div>
      )}

      {/* Mode toggle */}
      <div className="flex items-center gap-3 mb-4 text-sm">
        <span className="text-gray-400">{t('stats.uiLanguage') || 'Rodzaj treści'}:</span>
        <div className="flex gap-2">
          <button
            onClick={() => setIncludePolish(false)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              !includePolish ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'
            }`}
          >
            Tylko {targetLanguage}
          </button>
          <button
            onClick={() => setIncludePolish(true)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              includePolish ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'
            }`}
          >
            {targetLanguage} + polskie wyjaśnienia
          </button>
        </div>
      </div>

      {/* Lesson context banner */}
      {data?.lesson_title && !isCustomSearch && (
        <div className="flex items-center gap-3 bg-indigo-900/20 border border-indigo-700/30 rounded-lg px-4 py-3 mb-5">
          <BookOpen className="w-4 h-4 text-indigo-400 shrink-0" />
          <p className="text-sm text-indigo-300">
            Filmy dopasowane do dzisiejszej lekcji: <span className="font-semibold">{data.lesson_title}</span>
          </p>
        </div>
      )}

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Szukaj filmów... (np. niemiecka gramatyka, hiszpańska muzyka)"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
          {query && (
            <button type="button" onClick={() => setQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="w-4 h-4 text-gray-500 hover:text-gray-300" />
            </button>
          )}
        </div>
        <button
          type="submit"
          disabled={searching || !query.trim()}
          className="btn-primary px-4 disabled:opacity-50"
        >
          {searching ? '...' : 'Szukaj'}
        </button>
      </form>

      {/* Favorite creators */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Users className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Ulubieni twórcy</span>
        </div>
        <div className="flex flex-wrap gap-2 mb-2">
          {creators.map(name => (
            <button
              key={name}
              onClick={() => handleSuggestedClick(name)}
              disabled={searching}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-900/30 border border-indigo-700/40 text-indigo-300 text-xs hover:bg-indigo-700/40 transition-colors disabled:opacity-50"
            >
              {name}
              <span
                onClick={e => { e.stopPropagation(); removeCreator(name) }}
                className="text-indigo-500 hover:text-red-400 transition-colors cursor-pointer ml-0.5"
              >
                <X className="w-3 h-3" />
              </span>
            </button>
          ))}
          <form
            onSubmit={e => { e.preventDefault(); addCreator() }}
            className="flex items-center gap-1"
          >
            <input
              type="text"
              value={creatorInput}
              onChange={e => setCreatorInput(e.target.value)}
              placeholder="Dodaj twórcę..."
              className="bg-gray-800 border border-gray-700 rounded-full px-3 py-1.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500 w-36"
            />
            <button
              type="submit"
              disabled={!creatorInput.trim()}
              className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-40 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>

      {/* Suggested queries */}
      {data?.suggested_queries?.length > 0 && !isCustomSearch && (
        <div className="flex flex-wrap gap-2 mb-5">
          {data.suggested_queries.map((sq, i) => (
            <button
              key={i}
              onClick={() => handleSuggestedClick(sq)}
              disabled={searching}
              className={`px-3 py-1.5 rounded-full border text-xs transition-colors ${
                data.topic_queries?.includes(sq)
                  ? 'bg-indigo-900/30 border-indigo-700/50 text-indigo-300 hover:border-indigo-500'
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-500'
              }`}
            >
              {data.topic_queries?.includes(sq) && <span className="mr-1">📚</span>}
              {sq}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="card border-red-800/50 bg-red-900/10 mb-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Embedded player */}
      {activeVideoId && (
        <div className="card mb-6 p-0 overflow-hidden">
          <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
            <iframe
              className="absolute inset-0 w-full h-full"
              src={`https://www.youtube.com/embed/${activeVideoId}?autoplay=1`}
              title="YouTube video"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
          <div className="p-3 flex justify-end">
            <button
              onClick={() => setActiveVideoId(null)}
              className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200"
            >
              <X className="w-4 h-4" /> Zamknij odtwarzacz
            </button>
          </div>
        </div>
      )}

      {/* Favorites panel */}
      {showFavs && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-red-400 uppercase tracking-wide mb-3 flex items-center gap-2">
            <Heart className="w-4 h-4 fill-red-400" /> Ulubione filmy ({favorites.length})
          </h2>
          {favorites.length === 0 ? (
            <p className="text-gray-500 text-sm">Brak ulubionych. Kliknij serce na filmie żeby dodać.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {favorites.map(video => (
                <VideoCard
                  key={video.video_id}
                  video={video}
                  isActive={activeVideoId === video.video_id}
                  onPlay={() => setActiveVideoId(activeVideoId === video.video_id ? null : video.video_id)}
                  isFav={true}
                  onToggleFav={() => toggleFavorite(video)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {!showFavs && videos.length === 0 && !error && (
        <p className="text-center text-gray-500 mt-12">Brak wyników.</p>
      )}

      {/* Topic-related section */}
      {!showFavs && topicVideos.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-indigo-400 uppercase tracking-wide mb-3 flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            Powiązane z lekcją · {data?.lesson_topic}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {topicVideos.map(video => (
              <VideoCard
                key={video.video_id}
                video={video}
                isActive={activeVideoId === video.video_id}
                onPlay={() => setActiveVideoId(activeVideoId === video.video_id ? null : video.video_id)}
                highlight
                isFav={isFav(video.video_id)}
                onToggleFav={() => toggleFavorite(video)}
              />
            ))}
          </div>
        </div>
      )}

      {!showFavs && generalVideos.length > 0 && (
        <div>
          {topicVideos.length > 0 && (
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Ogólne Podkasty · poziom {data?.cefr_level}
            </h2>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {generalVideos.map(video => (
              <VideoCard
                key={video.video_id}
                video={video}
                isActive={activeVideoId === video.video_id}
                onPlay={() => setActiveVideoId(activeVideoId === video.video_id ? null : video.video_id)}
                isFav={isFav(video.video_id)}
                onToggleFav={() => toggleFavorite(video)}
              />
            ))}
          </div>
        </div>
      )}

      {!showFavs && isCustomSearch && videos.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map(video => (
            <VideoCard
              key={video.video_id}
              video={video}
              isActive={activeVideoId === video.video_id}
              onPlay={() => setActiveVideoId(activeVideoId === video.video_id ? null : video.video_id)}
              isFav={isFav(video.video_id)}
              onToggleFav={() => toggleFavorite(video)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function VideoCard({ video, isActive, onPlay, highlight, isFav, onToggleFav }) {
  return (
    <div className={`card p-0 overflow-hidden transition-all ${
      isActive ? 'ring-2 ring-indigo-500' : highlight ? 'ring-1 ring-indigo-800/40' : ''
    }`}>
      <div className="relative group cursor-pointer" onClick={onPlay}>
        {video.thumbnail ? (
          <img src={video.thumbnail} alt={video.title} className="w-full aspect-video object-cover" />
        ) : (
          <div className="w-full aspect-video bg-gray-800 flex items-center justify-center">
            <Youtube className="w-10 h-10 text-gray-600" />
          </div>
        )}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-14 h-14 bg-black/70 rounded-full flex items-center justify-center">
            <Play className="w-6 h-6 text-white ml-1" fill="white" />
          </div>
        </div>
        {isActive && (
          <div className="absolute top-2 left-2 bg-red-600 text-white text-xs px-2 py-0.5 rounded font-medium">
            ▶ ODTWARZANIE
          </div>
        )}
      </div>

      <div className="p-3">
        <h3 className="text-sm font-semibold text-gray-100 line-clamp-2 mb-1 leading-snug">{video.title}</h3>
        <p className="text-xs text-gray-500 mb-2">{video.channel} · {video.published_at}</p>
        {video.description && (
          <p className="text-xs text-gray-600 line-clamp-2">{video.description}</p>
        )}

        <div className="flex gap-2 mt-3">
          <button
            onClick={onPlay}
            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-red-700/30 hover:bg-red-700/50 text-red-300 text-xs font-medium transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            {isActive ? 'Zamknij' : 'Odtwórz'}
          </button>
          <button
            onClick={onToggleFav}
            className={`flex items-center justify-center px-2.5 py-1.5 rounded-lg text-xs transition-colors ${isFav ? 'bg-red-700/40 text-red-300 hover:bg-red-700/60' : 'bg-gray-800 hover:bg-gray-700 text-gray-500 hover:text-red-400'}`}
            title={isFav ? 'Usuń z ulubionych' : 'Dodaj do ulubionych'}
          >
            <Heart className={`w-3.5 h-3.5 ${isFav ? 'fill-red-400' : ''}`} />
          </button>
          <a
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 text-xs transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            YT
          </a>
        </div>
      </div>
    </div>
  )
}
