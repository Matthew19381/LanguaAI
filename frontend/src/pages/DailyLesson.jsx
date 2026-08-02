import { useState, useEffect, useRef, Fragment } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  BookOpen, CheckCircle, ChevronDown, ChevronUp,
  AlertTriangle, MessageSquare, PenTool, Star, Download,
  RefreshCw, Eye, EyeOff, FileText, BookmarkPlus, Loader2,
  History, ArrowRight, HelpCircle
} from 'lucide-react'
import { getUserId, getTodayLesson, getLesson, completeLesson, addFlashcardAI, evaluateProduction, generateNextLesson, generateConceptFlashcards, getDailyTest, getNews, searchYouTube, exportLessonPDF, exportObsidian, resetTodayLesson, getLessonAudioPackage } from '../api/client'
import { enqueueLessonComplete } from '../utils/offlineQueue'
import PlayButton from '../components/PlayButton'
import { PageLoader } from '../components/LoadingSpinner'
import SpecialChars from '../components/SpecialChars'
import { useLanguage } from '../hooks/useLanguage'

function renderMarkdown(text) {
  if (!text) return null
  return text.split('\n').map((line, i) => {
    if (line.startsWith('### ')) return <h4 key={i} className="font-semibold text-white mt-3 mb-1">{line.slice(4)}</h4>
    if (line.startsWith('## ')) return <h3 key={i} className="font-bold text-indigo-300 text-base mt-4 mb-1">{line.slice(3)}</h3>
    if (line.startsWith('# ')) return <h2 key={i} className="font-bold text-indigo-200 text-lg mt-4 mb-1">{line.slice(2)}</h2>
    if (line.startsWith('- ') || line.startsWith('* ')) {
      const content = parseBold(line.slice(2))
      return <li key={i} className="text-gray-300 ml-4 list-disc">{content}</li>
    }
    if (!line.trim()) return <br key={i} />
    return <p key={i} className="text-gray-300 leading-relaxed">{parseBold(line)}</p>
  })
}

function parseBold(text) {
  const parts = text.split(/\*\*(.*?)\*\*/g)
  return parts.map((p, j) =>
    j % 2 === 1 ? <strong key={j} className="text-white font-semibold">{p}</strong> : p
  )
}

const OBSIDIAN_OFFSETS = [
  { offset: -1, key: 'lesson.yesterday' },
  { offset: 0, key: 'lesson.today' },
  { offset: 1, key: 'lesson.tomorrow' },
  { offset: 2, key: 'lesson.dayAfterTomorrow' },
]

function readLessonCache() {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const uid = getUserId()
    const lang = localStorage.getItem('userLanguage') || ''
    const cached = localStorage.getItem(`lesson_cache_${uid}_${lang}_${today}`)
    return cached ? JSON.parse(cached) : null
  } catch { return null }
}

function clearLessonCache() {
  try {
    const uid = getUserId()
    const lang = localStorage.getItem('userLanguage') || ''
    const today = new Date().toISOString().slice(0, 10)
    localStorage.removeItem(`lesson_cache_${uid}_${lang}_${today}`)
  } catch (e) {
    console.error('Failed to clear lesson cache:', e)
  }
}

export default function DailyLesson() {
  const { lessonId } = useParams()
  const [lesson, setLesson] = useState(() => lessonId ? null : readLessonCache())
  const [loading, setLoading] = useState(() => lessonId ? true : !readLessonCache())
  const [error, setError] = useState('')
  const [completing, setCompleting] = useState(false)
  const [completed, setCompleted] = useState(() => {
    if (lessonId) return false
    const cached = readLessonCache()
    return cached ? !!cached.is_completed : false
  })
  const [expandedSections, setExpandedSections] = useState({
    explanation: true,
    vocabulary: true,
    dialogue: false,
    exercises: false,
    production: false,
    errorReview: false,
    comprehensibleInput: false,
    interleaved: false,
    outputForcing: false,
    pretest: true,
  })
  const [pdfLoading, setPdfLoading] = useState(false)
  const [audioPackageLoading, setAudioPackageLoading] = useState(false)
  const [obsidianLoading, setObsidianLoading] = useState(false)
  const [obsidianOffset, setObsidianOffset] = useState(0)
  const [obsidianUpload, setObsidianUpload] = useState(false)
  const [showObsidianMenu, setShowObsidianMenu] = useState(false)
  const [addedWords, setAddedWords] = useState(new Set())
  const [addingWord, setAddingWord] = useState(null)
  const [flashToast, setFlashToast] = useState('')
  const [regenerating, setRegenerating] = useState(false)
  const [productionAnswer, setProductionAnswer] = useState('')
  const productionRef = useRef(null)
  const [evaluating, setEvaluating] = useState(false)
  const [productionResult, setProductionResult] = useState(null)
  const [generatingNext, setGeneratingNext] = useState(false)
  const [conceptsLoading, setConceptsLoading] = useState(false)
  const [conceptsMsg, setConceptsMsg] = useState('')
  const [exportError, setExportError] = useState('')
  const navigate = useNavigate()
  const userId = getUserId()
  const { t } = useLanguage()

  useEffect(() => {
    if (!userId) {
      navigate('/placement')
      return
    }

    if (!lessonId) {
      // Try loading from localStorage cache first (today's lesson)
      const today = new Date().toISOString().slice(0, 10)
      const lang = localStorage.getItem('userLanguage') || ''
      const cacheKey = `lesson_cache_${userId}_${lang}_${today}`
      const cached = localStorage.getItem(cacheKey)
      if (cached) {
        try {
          const data = JSON.parse(cached)
          setLesson(data)
          setCompleted(data.is_completed)
          setLoading(false)
          // Revalidate in background
          getTodayLesson(userId)
            .then(fresh => {
              setLesson(fresh)
              setCompleted(fresh.is_completed)
              localStorage.setItem(cacheKey, JSON.stringify(fresh))
            })
            .catch(() => {})
          return
        } catch {}
      }
    }

    setLoading(true)
    const fetch = lessonId
      ? getLesson(parseInt(lessonId), userId)
      : getTodayLesson(userId)
    fetch
      .then(data => {
        setLesson(data)
        setCompleted(data.is_completed)
        if (!lessonId) {
          const today = new Date().toISOString().slice(0, 10)
          const lang = localStorage.getItem('userLanguage') || ''
          const cacheKey = `lesson_cache_${userId}_${lang}_${today}`
          localStorage.setItem(cacheKey, JSON.stringify(data))
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [userId, lessonId])

  const toggleSection = (key) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }))
  }

  // Mark the lesson tab done for today (shared with the offline path)
  const markLessonTabDone = () => {
    const today = new Date().toISOString().slice(0, 10)
    try {
      const raw = localStorage.getItem('daily_tabs')
      const stored = raw ? JSON.parse(raw) : { date: today, tabs: [] }
      if (stored.date !== today) stored.tabs = []
      if (!stored.tabs.includes('lesson')) {
        stored.tabs.push('lesson')
        localStorage.setItem('daily_tabs', JSON.stringify({ date: today, tabs: stored.tabs }))
      }
    } catch {}
  }

  // Optimistically flip the cached lesson to completed so a reload/revisit while
  // still offline shows it done (the queued event syncs the server later).
  const markLessonCacheCompleted = () => {
    try {
      const today = new Date().toISOString().slice(0, 10)
      const lang = localStorage.getItem('userLanguage') || ''
      const cacheKey = `lesson_cache_${userId}_${lang}_${today}`
      const cached = localStorage.getItem(cacheKey)
      if (cached) {
        const data = JSON.parse(cached)
        data.is_completed = true
        localStorage.setItem(cacheKey, JSON.stringify(data))
      }
    } catch {}
  }

  const completeOffline = () => {
    // Same idempotent pattern as exercises/flashcards: queue it, mark done
    // locally; useOfflineSync drains the outbox on reconnect.
    enqueueLessonComplete({ lessonId: lesson.lesson_id, userId })
    setCompleted(true)
    markLessonTabDone()
    markLessonCacheCompleted()
  }

  const handleComplete = async () => {
    if (!lesson) return
    setCompleting(true)
    // Known-offline: don't even attempt the request, queue straight away
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      completeOffline()
      setCompleting(false)
      return
    }
    try {
      await completeLesson(lesson.lesson_id, userId)
      setCompleted(true)
      // Clear lesson cache so next day fetches fresh lesson
      clearLessonCache()
      markLessonTabDone()
      // Reload to reflect new lesson state
      window.location.reload()
    } catch (e) {
      // No HTTP status = the request never reached the server (network drop):
      // fall back to the offline queue instead of surfacing an error.
      const status = e?.response?.status ?? e?.status
      if (!status) {
        completeOffline()
      } else {
        setError(e.message)
      }
    } finally {
      setCompleting(false)
    }
  }

  const handleGenerateNext = async () => {
    if (!userId) return
    setGeneratingNext(true)
    try {
      const data = await generateNextLesson(userId)
      setLesson(data)
      setCompleted(data.is_completed)
      setExpandedSections({
        explanation: true, vocabulary: true, dialogue: false,
        exercises: false, production: false, errorReview: false,
        comprehensibleInput: false, interleaved: false, outputForcing: false,
      })

      // Pre-fetch test, news and videos in the background so they're ready immediately
      const today = new Date().toISOString().slice(0, 10)
      const lang = localStorage.getItem('userLanguage') || ''
      localStorage.removeItem(`test_cache_${userId}_${lang}_${today}`)
      getDailyTest(userId).then(test => {
        localStorage.setItem(`test_cache_${userId}_${lang}_${today}`, JSON.stringify(test))
      }).catch(() => {})
      getNews(userId).catch(() => {})
      searchYouTube(userId, '').catch(() => {})
    } catch (e) {
      setError(e.message)
    } finally {
      setGeneratingNext(false)
    }
  }

  const handleRegenerateLesson = async () => {
    if (!lesson || !userId) return
    if (!window.confirm(t('lesson.regenerateConfirm') || 'Czy na pewno chcesz wygenerować nową lekcję? Obecna lekcja zostanie usunięta.')) return
    setRegenerating(true)
    try {
      // Delete today's lesson so it gets regenerated on next fetch
      await resetTodayLesson(userId)
      // Clear cache and reload
      clearLessonCache()
      setLesson(null)
      setLoading(true)
      const data = await getTodayLesson(userId)
      setLesson(data)
      setCompleted(data.is_completed)
      setExpandedSections({
        explanation: true, vocabulary: true, dialogue: false,
        exercises: false, production: false, errorReview: false,
        comprehensibleInput: false, interleaved: false, outputForcing: false,
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setRegenerating(false)
      setLoading(false)
    }
  }

  const handleConceptFlashcards = async () => {
    if (!lesson) return
    setConceptsLoading(true)
    setConceptsMsg('')
    try {
      const res = await generateConceptFlashcards(lesson.lesson_id, userId)
      if (!res.success) {
        setConceptsMsg(res.message || 'Brak gramatyki w tej lekcji.')
      } else if (res.created > 0 && res.skipped > 0) {
        setConceptsMsg(`Dodano ${res.created} fiszek (${res.skipped} już istniało) ✓`)
      } else if (res.created > 0) {
        setConceptsMsg(`Dodano ${res.created} fiszek z koncepcjami ✓`)
      } else {
        setConceptsMsg(`Wszystkie ${res.total_concepts || ''} koncepcje już są w fiszkach.`)
      }
    } catch (e) {
      setConceptsMsg('Błąd: ' + e.message)
    } finally {
      setConceptsLoading(false)
    }
  }

  const handleDownloadAudioPackage = async () => {
    if (!lesson) return
    setAudioPackageLoading(true)
    try {
      const response = await getLessonAudioPackage(lesson.lesson_id)
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `Lekcja_${lesson.lesson_id}_audio.zip`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setExportError(t('lesson.audioDownloadError') || 'Nie udało się pobrać pakietu audio. Spróbuj ponownie.')
      setTimeout(() => setExportError(''), 5000)
    } finally {
      setAudioPackageLoading(false)
    }
  }

  const handleDownloadPDF = async () => {
    if (!lesson) return
    setPdfLoading(true)
    try {
      const response = await exportLessonPDF(lesson.lesson_id, userId)
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `lesson_${lesson.lesson_id}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setExportError(t('lesson.pdfDownloadError') || 'Nie udało się pobrać PDF. Spróbuj ponownie.')
      setTimeout(() => setExportError(''), 5000)
    } finally {
      setPdfLoading(false)
    }
  }

  const handleExportObsidian = async () => {
    if (!lesson) return
    setObsidianLoading(true)
    setShowObsidianMenu(false)
    try {
      const response = await exportObsidian(lesson.lesson_id, userId, obsidianOffset, obsidianUpload)
      if (obsidianUpload) {
        const data = response.data
        alert(`Uploaded to Google Drive: ${data.url || 'success'}`)
      } else {
        const url = URL.createObjectURL(new Blob([response.data], { type: 'text/markdown' }))
        const link = document.createElement('a')
        link.href = url
        link.download = `lesson_${lesson.lesson_id}.md`
        link.click()
        URL.revokeObjectURL(url)
      }
    } catch (e) {
      setExportError(t('lesson.obsidianExportError') || 'Nie udało się wyeksportować do Obsidian. Spróbuj ponownie.')
      setTimeout(() => setExportError(''), 5000)
    } finally {
      setObsidianLoading(false)
    }
  }

  const handleAddFlashcard = async (word) => {
    if (!word || addedWords.has(word)) return
    setAddingWord(word)
    try {
      await addFlashcardAI(userId, word)
      setAddedWords(prev => new Set([...prev, word]))
      setFlashToast(`"${word}" ${t('lesson.addedToFlash')}`)
      setTimeout(() => setFlashToast(''), 2500)
    } catch (e) {
      console.error('Failed to add flashcard:', e)
      setFlashToast(t('lesson.addFlashError'))
      setTimeout(() => setFlashToast(''), 2500)
    } finally {
      setAddingWord(null)
    }
  }

  const handleEvaluateProduction = async () => {
    if (!productionAnswer.trim() || !lesson) return
    setEvaluating(true)
    setProductionResult(null)
    try {
      const result = await evaluateProduction(lesson.lesson_id, {
        userId,
        user_answer: productionAnswer,
        instruction: content.production_task?.instruction || '',
        language: lesson.language || 'German',
        cefr_level: lesson.cefr_level || 'B1',
      })
      setProductionResult(result)
    } catch (e) {
      setProductionResult({ success: false, feedback: 'Błąd: ' + e.message, score: 0, corrections: [], improved_version: '' })
    } finally {
      setEvaluating(false)
    }
  }

  if (loading) return <PageLoader text={t('lesson.loading')} />

  if (error) {
    return (
      <div className="page-container">
        <div className="card border-red-700/30 bg-red-900/10 text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h2 className="text-xl font-semibold mb-2">{t('lesson.errorTitle')}</h2>
          <p className="text-gray-400 mb-4">{error}</p>
          {error.includes('study plan') && (
            <button onClick={() => navigate('/placement')} className="btn-primary">
              {t('lesson.takePlacement')}
            </button>
          )}
        </div>
      </div>
    )
  }

  if (!lesson) return null

  const content = lesson.content || {}

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="badge-blue">{t('lesson.day')} {lesson.day_number}</span>
            {completed && <span className="badge-green flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> {t('lesson.completed')}
            </span>}
          </div>
          <h1 className="text-2xl font-bold">{lesson.title}</h1>
          <p className="text-gray-400 mt-1">{lesson.topic}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/lesson/history')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
            title={t('history.title')}
          >
            <History className="w-4 h-4" />
            <span className="hidden sm:block">{t('history.title')}</span>
          </button>
          {!completed && (
            <button
              onClick={handleRegenerateLesson}
              disabled={regenerating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-700 hover:bg-orange-600 text-white text-sm font-medium transition-colors disabled:opacity-50"
              title={t('lesson.regenerate') || 'Wygeneruj nową lekcję'}
            >
              <RefreshCw className={`w-4 h-4 ${regenerating ? 'animate-spin' : ''}`} />
              <span className="hidden sm:block">{t('lesson.regenerate') || 'Nowa lekcja'}</span>
            </button>
          )}
          <button
            onClick={handleDownloadPDF}
            disabled={pdfLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors disabled:opacity-50"
            title="Download PDF"
          >
            <Download className="w-4 h-4" />
            {pdfLoading ? t('lesson.generating') : t('lesson.pdf')}
          </button>
          <button
            onClick={handleDownloadAudioPackage}
            disabled={audioPackageLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg dark:bg-indigo-700 bg-indigo-600 dark:hover:bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors disabled:opacity-50"
            title="Pobierz audio na telefon (ZIP z MP3)"
          >
            <Download className="w-4 h-4" />
            {audioPackageLoading ? t('lesson.generating') : '🎧 Audio ZIP'}
          </button>

          {/* Obsidian Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowObsidianMenu(m => !m)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg dark:bg-gray-800 bg-gray-100 dark:hover:bg-gray-700 hover:bg-gray-200 dark:text-gray-300 text-gray-600 text-sm transition-colors"
              title={t('lesson.exportObsidian')}
            >
              <FileText className="w-4 h-4" />
              <span className="hidden sm:block">MD</span>
              <ChevronDown className="w-3 h-3" />
            </button>

            {showObsidianMenu && (
              <div className="absolute right-0 top-full mt-1 z-50 dark:bg-gray-800 bg-white dark:border dark:border-gray-700 border border-gray-200 rounded-lg shadow-xl p-3 min-w-[220px]">
                <p className="text-xs dark:text-gray-400 text-gray-500 mb-2 font-medium">{t('lesson.exportObsidian')}</p>

                {/* Day offset selector */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {OBSIDIAN_OFFSETS.map(({ offset, key }) => (
                    <button
                      key={offset}
                      onClick={() => setObsidianOffset(offset)}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        obsidianOffset === offset
                          ? 'bg-indigo-600 text-white'
                          : 'dark:bg-gray-700 bg-gray-100 dark:text-gray-300 text-gray-600 dark:hover:bg-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {t(key)}
                    </button>
                  ))}
                </div>

                {/* Upload toggle */}
                <div className="flex gap-1 mb-3">
                  <button
                    onClick={() => setObsidianUpload(false)}
                    className={`flex-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                      !obsidianUpload ? 'bg-indigo-600 text-white' : 'dark:bg-gray-700 bg-gray-100 dark:text-gray-300 text-gray-600 dark:hover:bg-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {t('lesson.downloadLocal')}
                  </button>
                  <button
                    onClick={() => setObsidianUpload(true)}
                    className={`flex-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                      obsidianUpload ? 'bg-indigo-600 text-white' : 'dark:bg-gray-700 bg-gray-100 dark:text-gray-300 text-gray-600 dark:hover:bg-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {t('lesson.sendToDrive')}
                  </button>
                </div>

                <button
                  onClick={handleExportObsidian}
                  disabled={obsidianLoading}
                  className="w-full px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {obsidianLoading ? '...' : t('lesson.exportObsidian')}
                </button>
              </div>
            )}
          </div>

          <BookOpen className="w-8 h-8 text-indigo-400" />
        </div>
      </div>

      {/* Explanation */}
      <Section
        title={t('lesson.grammar')}
        icon={<BookOpen className="w-5 h-5" />}
        expanded={expandedSections.explanation}
        onToggle={() => toggleSection('explanation')}
      >
        <div className="prose prose-invert max-w-none">
          {renderMarkdown(content.explanation)}
        </div>
        {content.explanation && (
          <div className="mt-2 flex items-center gap-2">
            <PlayButton
              text={content.explanation
                .replace(/#{1,6}\s*/g, '')
                .replace(/\*\*(.+?)\*\*/g, '$1')
                .replace(/\*(.+?)\*/g, '$1')
                .replace(/`(.+?)`/g, '$1')
                .replace(/\n{2,}/g, '. ')
                .replace(/\n/g, ' ')
                .trim()
                .slice(0, 400)}
              language={lesson.language}
            />
            <span className="text-xs text-gray-500">Przesłuchaj wyjaśnienie</span>
          </div>
        )}
        <div className="mt-3">
          <button
            onClick={handleConceptFlashcards}
            disabled={conceptsLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-900/30 hover:bg-purple-900/50 border border-purple-700/40 text-purple-300 text-xs font-medium transition-colors disabled:opacity-50"
          >
            <BookmarkPlus className="w-3.5 h-3.5" />
            {conceptsLoading ? 'Generowanie...' : 'Dodaj koncepcje do fiszek'}
          </button>
          {conceptsMsg && <p className="text-xs text-emerald-400 mt-1">{conceptsMsg}</p>}
        </div>
      </Section>

      {/* Pretest (SCI-2): guess before being taught — wrong guesses are fine */}
      {content.pretest?.length > 0 && (
        <Section
          title={t('lesson.pretest')}
          icon={<HelpCircle className="w-5 h-5 text-amber-400" />}
          expanded={expandedSections.pretest}
          onToggle={() => toggleSection('pretest')}
        >
          <PretestCard items={content.pretest} t={t} />
        </Section>
      )}

      {/* Vocabulary */}
      {content.vocabulary?.length > 0 && (
        <Section
          title={`${t('lesson.vocabulary')} (${content.vocabulary.length} ${t('lesson.words')})`}
          icon={<Star className="w-5 h-5" />}
          expanded={expandedSections.vocabulary}
          onToggle={() => toggleSection('vocabulary')}
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left border-b border-gray-700">
                  <th className="pb-2 text-gray-400 font-medium text-sm">{t('lesson.word')}</th>
                  <th className="pb-2 text-gray-400 font-medium text-sm">{t('lesson.translation')}</th>
                  <th className="pb-2 text-gray-400 font-medium text-sm hidden md:table-cell">{t('lesson.example')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {content.vocabulary.map((item, i) => (
                  <tr key={i} className="hover:bg-gray-800/50">
                    <td className="py-2.5 pr-4">
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-indigo-300">{item.word}</span>
                        <PlayButton text={item.word} language={lesson.language} />
                        <button
                          onClick={() => handleAddFlashcard(item.word)}
                          disabled={addingWord === item.word}
                          title={t('lesson.addToFlash')}
                          className={`inline-flex items-center justify-center w-5 h-5 rounded hover:bg-gray-700 transition-colors ${
                            addedWords.has(item.word) ? 'text-emerald-400' : 'text-gray-500 hover:text-indigo-300'
                          } ${addingWord === item.word ? 'opacity-50' : ''}`}
                        >
                          {addingWord === item.word ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : addedWords.has(item.word) ? (
                            <CheckCircle className="w-3 h-3" />
                          ) : (
                            <BookmarkPlus className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className="text-emerald-300">{item.translation}</span>
                    </td>
                    <td className="py-2.5 text-gray-400 text-sm hidden md:table-cell">
                      <div className="flex items-center gap-1">
                        <span>{item.example}</span>
                        {item.example && <PlayButton text={item.example} language={lesson.language} />}
                      </div>
                      {item.example_translation && (
                        <div className="text-gray-500 text-xs mt-0.5 italic">↳ {item.example_translation}</div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Dialogue */}
      {content.dialogue && (
        <Section
          title={t('lesson.dialogue')}
          icon={<MessageSquare className="w-5 h-5" />}
          expanded={expandedSections.dialogue}
          onToggle={() => toggleSection('dialogue')}
        >
          {content.dialogue.context && (
            <p className="text-gray-400 text-sm italic mb-4 bg-gray-800 rounded-lg p-3">
              {content.dialogue.context}
            </p>
          )}
          <div className="space-y-3">
            {(() => {
              const lines = content.dialogue.lines || []
              const speakers = []
              lines.forEach(line => {
                const s = line.speaker || 'A'
                if (!speakers.includes(s)) speakers.push(s)
              })
              return lines.map((line, i) => {
                const spk = line.speaker || (i % 2 === 0 ? speakers[0] : (speakers[1] || 'B'))
                const isB = speakers.indexOf(spk) > 0
                return (
                <div
                  key={i}
                  className={`flex gap-3 ${isB ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${
                    isB ? 'bg-purple-700' : 'bg-indigo-700'
                  }`}>
                    {spk.slice(0, 2)}
                  </div>
                  <div className={`max-w-sm rounded-2xl px-4 py-2.5 ${
                    isB
                      ? 'bg-gray-700 rounded-tr-sm'
                      : 'bg-gray-800 rounded-tl-sm'
                  }`}>
                    <div className="flex items-start gap-1.5">
                      <p className="font-medium flex-1">{line.text}</p>
                      <PlayButton text={line.text} language={lesson.language} />
                    </div>
                    {line.translation && (
                      <p className="text-gray-400 text-sm mt-0.5 italic">{line.translation}</p>
                    )}
                  </div>
                </div>
              )
              })
            })()}
          </div>
        </Section>
      )}

      {/* Exercises */}
      {content.exercises?.length > 0 && (
        <Section
          title={`${t('lesson.exercises')} (${content.exercises.length})`}
          icon={<PenTool className="w-5 h-5" />}
          expanded={expandedSections.exercises}
          onToggle={() => toggleSection('exercises')}
        >
          <div className="space-y-4">
            {content.exercises.map((ex, i) => (
              <ExerciseCard key={i} exercise={ex} number={i + 1} language={lesson.language} lessonId={lesson.lesson_id} t={t} />
            ))}
          </div>
        </Section>
      )}

      {/* Production Task */}
      {content.production_task && (
        <Section
          title={t('lesson.productionTask')}
          icon={<PenTool className="w-5 h-5" />}
          expanded={expandedSections.production}
          onToggle={() => toggleSection('production')}
        >
          <div className="bg-indigo-900/20 border border-indigo-700/30 rounded-lg p-4">
            <p className="font-medium text-indigo-300 mb-2">{content.production_task.instruction}</p>
            {content.production_task.example && (
              <p className="text-gray-400 text-sm italic">
                {t('lesson.exampleLabel')} {content.production_task.example}
              </p>
            )}
          </div>
          <textarea
            ref={productionRef}
            className="input-field mt-3 h-24 resize-none"
            placeholder={t('lesson.writeResponse')}
            value={productionAnswer}
            onChange={e => setProductionAnswer(e.target.value)}
          />
          <SpecialChars language={lesson.language} inputRef={productionRef} value={productionAnswer} onChange={setProductionAnswer} />
          <p className="text-xs text-gray-500 mb-2">{t('lesson.aiWillEvaluate')}</p>
          <button
            onClick={handleEvaluateProduction}
            disabled={evaluating || !productionAnswer.trim()}
            className="mt-2 flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            {evaluating ? <><Loader2 className="w-4 h-4 animate-spin" /> {t('lesson.evaluating')}</> : t('lesson.checkAnswer')}
          </button>
          {productionResult && (
            <div className={`mt-3 rounded-lg p-4 ${productionResult.success !== false ? 'bg-emerald-900/10 border border-emerald-700/30' : 'bg-red-900/10 border border-red-700/30'}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-2xl font-bold ${
                  productionResult.score >= 70 ? 'text-emerald-400' :
                  productionResult.score >= 40 ? 'text-yellow-400' : 'text-red-400'
                }`}>{productionResult.score}/100</span>
                <span className="text-gray-400 text-sm">{t('lesson.pts')}</span>
              </div>
              {productionResult.feedback && (
                <p className="text-gray-300 text-sm mb-2">{productionResult.feedback}</p>
              )}
              {productionResult.corrections?.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs text-gray-500 mb-1">{t('lesson.corrections')}</p>
                  {productionResult.corrections.map((c, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="text-red-400 line-through">{c.error}</span>
                      <span className="text-gray-500">→</span>
                      <span className="text-emerald-400">{c.correction}</span>
                    </div>
                  ))}
                </div>
              )}
              {productionResult.improved_version && (
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-xs text-gray-500 mb-1">{t('lesson.betterVersion')}</p>
                  <p className="text-gray-200 text-sm">{productionResult.improved_version}</p>
                </div>
              )}
            </div>
          )}
        </Section>
      )}

      {/* Error Review */}
      {content.error_review?.length > 0 && (
        <Section
          title={`${t('lesson.errorReview')} (${content.error_review.length})`}
          icon={<AlertTriangle className="w-5 h-5 text-yellow-400" />}
          expanded={expandedSections.errorReview}
          onToggle={() => toggleSection('errorReview')}
        >
          <div className="space-y-3">
            {content.error_review.map((err, i) => (
              <div key={i} className="bg-yellow-900/10 border border-yellow-700/30 rounded-lg p-4">
                <div className="flex items-start gap-2 mb-2 flex-wrap">
                  <div className="flex items-center gap-1">
                    <span className="text-red-400 font-medium line-through">{err.error}</span>
                    <PlayButton text={err.error} language={lesson.language} />
                  </div>
                  <span className="text-gray-500">→</span>
                  <div className="flex items-center gap-1">
                    <span className="text-emerald-400 font-medium">{err.correction}</span>
                    <PlayButton text={err.correction} language={lesson.language} />
                  </div>
                </div>
                <p className="text-gray-400 text-sm">{err.explanation}</p>
                {err.practice && (
                  <div className="flex items-center gap-1 mt-2">
                    <p className="text-yellow-300 text-sm italic">{t('lesson.practiceLabel')} {err.practice}</p>
                    <PlayButton text={err.practice} language={lesson.language} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Comprehensible Input (i+1) */}
      {content.comprehensible_input?.text && (
        <Section
          title={t('lesson.readingPractice')}
          icon={<BookOpen className="w-5 h-5 text-teal-400" />}
          expanded={expandedSections.comprehensibleInput}
          onToggle={() => toggleSection('comprehensibleInput')}
        >
          <div className="bg-teal-900/10 border border-teal-700/30 rounded-lg p-4 mb-3 relative">
            <p className="text-xs text-teal-600 mb-2 italic">Kliknij słowo → dodaj do fiszek</p>
            <p className="text-gray-200 leading-relaxed">
              {content.comprehensible_input.text.split(/(\S+)/).map((part, i) => {
                const newWords = content.comprehensible_input.new_words || []
                const cleaned = part.replace(/[.,!?;:'"()[\]]/g, '').toLowerCase()
                const isWord = cleaned.length > 1
                const isNew = cleaned.length > 2 && newWords.some(w => {
                  const wl = w.toLowerCase().replace(/[.,!?;:'"()[\]]/g, '')
                  return wl.length > 2 && (
                    cleaned === wl ||
                    cleaned.includes(wl) ||
                    wl.includes(cleaned) ||
                    (cleaned.length >= 4 && wl.length >= 4 && cleaned.slice(0, 4) === wl.slice(0, 4))
                  )
                })
                const isAdded = addedWords.has(cleaned)
                if (isNew) {
                  return (
                    <mark
                      key={i}
                      className={`rounded px-0.5 cursor-pointer transition-colors ${isAdded ? 'bg-emerald-500/30 text-emerald-200' : 'bg-yellow-500/30 text-yellow-200 hover:bg-yellow-500/50'}`}
                      onClick={() => handleAddFlashcard(cleaned)}
                      title={t('lesson.addToFlash')}
                    >{part}</mark>
                  )
                }
                if (isWord) {
                  return (
                    <span
                      key={i}
                      className={`cursor-pointer transition-colors rounded px-0.5 ${isAdded ? 'text-emerald-400' : 'hover:bg-teal-700/30 hover:text-teal-200'}`}
                      onClick={() => handleAddFlashcard(cleaned)}
                      title={t('lesson.addToFlash')}
                    >{part}</span>
                  )
                }
                return <span key={i}>{part}</span>
              })}
            </p>
            <div className="mt-2 flex items-center justify-between">
              <button
                onClick={() => handleAddFlashcard(content.comprehensible_input.text.trim())}
                disabled={addingWord === 'full_text'}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-700/30 hover:bg-teal-600/40 text-teal-200 text-sm transition-colors disabled:opacity-50"
              >
                {addingWord === 'full_text' ? <Loader2 className="w-3 h-3 animate-spin" /> : <BookmarkPlus className="w-3 h-3" />}
                Dodaj całe zdanie do fiszek
              </button>
              <PlayButton text={content.comprehensible_input.text} language={lesson.language} />
            </div>
          </div>
          {content.comprehensible_input.new_words?.length > 0 && (
            <div className="mb-3">
              <p className="text-sm text-gray-400 mb-1">{t('lesson.newWords')}</p>
              <div className="flex flex-wrap gap-2">
                {content.comprehensible_input.new_words.map((w, i) => (
                  <div key={i} className="flex items-center gap-1 bg-yellow-500/20 text-yellow-300 px-2 py-0.5 rounded text-sm">
                    <span>{w}</span>
                    <PlayButton text={w} language={lesson.language} />
                    <button
                      onClick={() => handleAddFlashcard(w)}
                      disabled={addingWord === w}
                      title={t('lesson.addToFlash')}
                      className={`transition-colors ${addedWords.has(w) ? 'text-emerald-400' : 'text-yellow-500 hover:text-yellow-200'}`}
                    >
                      {addingWord === w ? <Loader2 className="w-3 h-3 animate-spin" /> : addedWords.has(w) ? <CheckCircle className="w-3 h-3" /> : <BookmarkPlus className="w-3 h-3" />}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          {content.comprehensible_input.comprehension_questions?.length > 0 && (
            <div>
              <p className="text-sm text-gray-400 mb-2">{t('lesson.comprehensionCheck')}</p>
              <div className="space-y-2">
                {content.comprehensible_input.comprehension_questions.map((q, i) => (
                  <ComprehensionQ key={i} question={q.question} answer={q.answer} t={t} />
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* Interleaved Review */}
      {content.interleaved_review?.length > 0 && (
        <Section
          title={`${t('lesson.mixedReview')} (${content.interleaved_review.length} ${t('lesson.questions')})`}
          icon={<RefreshCw className="w-5 h-5 text-orange-400" />}
          expanded={expandedSections.interleaved}
          onToggle={() => toggleSection('interleaved')}
        >
          <p className="text-gray-400 text-sm mb-3">{t('lesson.reviewPrevious')}</p>
          <div className="space-y-3">
            {content.interleaved_review.map((item, i) => (
              <div key={i} className="bg-orange-900/10 border border-orange-700/30 rounded-lg p-3">
                <p className="text-xs text-orange-400 mb-1">{t('lesson.topic')} {item.topic}</p>
                <ComprehensionQ question={item.question} answer={item.answer} t={t} />
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Output Forcing */}
      {content.output_forcing?.text && (
        <Section
          title={t('lesson.outputForcing')}
          icon={<PenTool className="w-5 h-5 text-pink-400" />}
          expanded={expandedSections.outputForcing}
          onToggle={() => toggleSection('outputForcing')}
        >
          <OutputForcingCard
            instruction={content.output_forcing.instruction}
            text={content.output_forcing.text}
            translation={content.output_forcing.translation}
            language={lesson.language}
            t={t}
          />
        </Section>
      )}

      {/* Complete Button */}
      {!completed ? (
        <button
          className="btn-success w-full py-3 mt-4 flex items-center justify-center gap-2 text-lg"
          onClick={handleComplete}
          disabled={completing}
        >
          {completing ? (
            <>{t('lesson.marking')}</>
          ) : (
            <>
              <CheckCircle className="w-5 h-5" />
              {t('lesson.markComplete')}
            </>
          )}
        </button>
      ) : (
        <div className="card border-emerald-700/30 bg-emerald-900/10 text-center mt-4">
          <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
          <p className="text-emerald-300 font-semibold">{t('lesson.lessonCompleted')}</p>
          <p className="text-gray-400 text-sm mt-1">{t('lesson.earnedXP')}</p>
          <div className="flex flex-wrap gap-2 justify-center mt-3">
            <button
              className="btn-primary flex items-center gap-2"
              onClick={() => navigate('/test')}
            >
              {t('lesson.takeDailyTest')}
            </button>
            <button
              className="btn-secondary flex items-center gap-2"
              onClick={handleGenerateNext}
              disabled={generatingNext}
            >
              {generatingNext ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              {t('lesson.nextLesson') || 'Następna lekcja'}
            </button>
            <button
              className="btn-secondary flex items-center gap-2"
              onClick={() => navigate('/lesson/history')}
            >
              <History className="w-4 h-4" />
              {t('history.title')}
            </button>
          </div>
        </div>
      )}
      {flashToast && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 bg-emerald-700 text-white px-4 py-2 rounded-xl shadow-lg text-sm font-medium animate-fade-in">
          {flashToast}
        </div>
      )}
      {exportError && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 bg-red-700 text-white px-4 py-2 rounded-xl shadow-lg text-sm font-medium animate-fade-in">
          {exportError}
        </div>
      )}
    </div>
  )
}

function Section({ title, icon, expanded, onToggle, children }) {
  return (
    <div className="card mb-4">
      <button
        className="flex items-center justify-between w-full text-left"
        onClick={onToggle}
      >
        <div className="flex items-center gap-2 text-indigo-300">
          {icon}
          <h2 className="font-semibold">{title}</h2>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        )}
      </button>
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          {children}
        </div>
      )}
    </div>
  )
}

function ComprehensionQ({ question, answer, t }) {
  const [show, setShow] = useState(false)
  return (
    <div className="bg-gray-800 rounded p-3">
      <p className="text-gray-200 text-sm">{question}</p>
      <button
        onClick={() => setShow(s => !s)}
        className="text-indigo-400 hover:text-indigo-300 text-xs mt-1"
      >
        {show ? t('lesson.hideAnswer') : t('lesson.showAnswer')}
      </button>
      {show && <p className="text-emerald-300 text-sm mt-1">{answer}</p>}
    </div>
  )
}

function TranslationReveal({ translation }) {
  const [show, setShow] = useState(false)
  if (!translation) return null
  return (
    <button
      onClick={() => setShow(s => !s)}
      className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
    >
      <Eye className="w-3 h-3" />
      {show ? <span className="text-emerald-300">{translation}</span> : 'Pokaż tłumaczenie'}
    </button>
  )
}

function PretestCard({ items, t }) {
  // SCI-2 pretesting: the learner guesses each word's meaning BEFORE the lesson
  // teaches it. A wrong guess is expected and pedagogically useful — no scoring,
  // no XP. After choosing, we reveal the correct answer and move on.
  return (
    <div>
      <p className="text-amber-300/90 text-sm mb-3">
        {t('lesson.pretestHint')}
      </p>
      <div className="space-y-4">
        {items.map((item, i) => (
          <PretestItem key={i} item={item} t={t} />
        ))}
      </div>
    </div>
  )
}

function PretestItem({ item, t }) {
  const [chosen, setChosen] = useState(null)
  const answered = chosen !== null
  return (
    <div className="bg-amber-900/10 border border-amber-700/30 rounded-lg p-3">
      <p className="text-gray-200 text-sm mb-2">
        {item.prompt || t('lesson.pretestGuess')} <span className="font-semibold text-amber-200">{item.word}</span>
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {item.options.map((opt, j) => {
          const isCorrect = opt === item.answer
          const isChosen = opt === chosen
          let cls = 'bg-gray-800 hover:bg-gray-700 text-gray-200'
          if (answered && isCorrect) cls = 'bg-emerald-800/60 text-emerald-100 border border-emerald-600'
          else if (answered && isChosen) cls = 'bg-red-900/50 text-red-200 border border-red-700'
          else if (answered) cls = 'bg-gray-800/50 text-gray-500'
          return (
            <button
              key={j}
              onClick={() => !answered && setChosen(opt)}
              disabled={answered}
              className={`text-left text-sm px-3 py-2 rounded-lg transition-colors ${cls}`}
            >
              {opt}
            </button>
          )
        })}
      </div>
      {answered && (
        <p className="text-xs text-gray-400 mt-2">
          {chosen === item.answer ? t('lesson.pretestCorrect') : t('lesson.pretestWrongOk')}
        </p>
      )}
    </div>
  )
}

function OutputForcingCard({ instruction, text, translation, language, t }) {
  const words = text ? text.split(/\s+/) : []
  const [revealedCount, setRevealedCount] = useState(0)
  const [recallMode, setRecallMode] = useState(false)
  const [userRecall, setUserRecall] = useState('')
  const recallRef = useRef(null)
  const [showFull, setShowFull] = useState(false)

  const similarity = () => {
    if (!userRecall || !text) return 0
    const a = userRecall.toLowerCase().split(/\s+/)
    const b = text.toLowerCase().split(/\s+/)
    const matches = a.filter(w => b.includes(w)).length
    return Math.round((matches / b.length) * 100)
  }

  const score = recallMode && userRecall ? similarity() : null

  const revealNextWord = () => {
    if (revealedCount < words.length) setRevealedCount(r => r + 1)
  }

  const revealAll = () => setRevealedCount(words.length)

  return (
    <div>
      <p className="text-gray-400 text-sm mb-3">{instruction}</p>

      {!recallMode ? (
        <div>
          {/* Word-by-word reveal area */}
          <div className="bg-pink-900/10 border border-pink-700/30 rounded-lg p-4 mb-3">
            <p className="text-gray-100 leading-relaxed text-lg">
              {words.map((word, i) => (
                <span key={i}>
                  {i < revealedCount
                    ? <span className="text-gray-100">{word} </span>
                    : <span className="bg-pink-900/60 rounded px-1 text-transparent select-none cursor-pointer hover:bg-pink-800/60 transition-colors" onClick={revealNextWord}>{'_'.repeat(word.length)} </span>
                  }
                </span>
              ))}
            </p>
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <PlayButton text={text} language={language} />
              {translation && <TranslationReveal translation={translation} />}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={revealNextWord}
              disabled={revealedCount >= words.length}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-pink-700 hover:bg-pink-600 disabled:opacity-40 text-white text-sm transition-colors"
            >
              <Eye className="w-4 h-4" /> Pokaż słowo ({revealedCount}/{words.length})
            </button>
            <button
              onClick={revealAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm transition-colors"
            >
              Pokaż wszystko
            </button>
            <button
              onClick={() => { setRevealedCount(0); setRecallMode(true) }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
            >
              <EyeOff className="w-4 h-4" /> {t('lesson.hideTest')}
            </button>
          </div>
        </div>
      ) : (
        <div>
          <p className="text-gray-400 text-sm mb-2">{t('lesson.recallText')}</p>
          <textarea
            ref={recallRef}
            className="input-field h-24 resize-none mb-2"
            placeholder={t('lesson.writeRemember')}
            value={userRecall}
            onChange={e => setUserRecall(e.target.value)}
          />
          <SpecialChars language={language} inputRef={recallRef} value={userRecall} onChange={setUserRecall} />
          <div className="flex items-center gap-3 flex-wrap mt-1">
            {score !== null && (
              <span className={`text-sm font-bold ${
                score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {t('lesson.similarity')} {score}%
              </span>
            )}
            <button
              onClick={() => { setRecallMode(false); setRevealedCount(0) }}
              className="flex items-center gap-1 text-gray-400 hover:text-gray-200 text-sm"
            >
              <Eye className="w-4 h-4" /> {t('lesson.showOriginal')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ExerciseCard({ exercise, number, language, lessonId, t }) {
  const [revealedCount, setRevealedCount] = useState(0)
  const [userAnswer, setUserAnswer] = useState('')
  const [selectedOption, setSelectedOption] = useState('')
  const [checked, setChecked] = useState(false)
  const [isCorrect, setIsCorrect] = useState(null)
  const inputRef = useRef(null)

  const handleCheck = () => {
    if (!userAnswer.trim()) return
    const correct = String(exercise.answer || '').trim().toLowerCase()
    const given = userAnswer.trim().toLowerCase()
    const correct_ = given === correct || correct.includes(given) || given.includes(correct)
    setIsCorrect(correct_)
    setChecked(true)
  }

  const answerWords = exercise.answer ? String(exercise.answer).split(' ') : []
  const totalWords = answerWords.length
  const isAllRevealed = revealedCount >= totalWords && totalWords > 0

  const handleRevealClick = () => {
    if (isAllRevealed) {
      setRevealedCount(0)
    } else {
      setRevealedCount(c => Math.min(c + 1, totalWords))
    }
  }

  const revealBtnLabel = revealedCount === 0
    ? t('lesson.showExerciseAnswer')
    : isAllRevealed
    ? t('lesson.hideExerciseAnswer')
    : (t('lesson.nextWord') || 'Następne słowo')

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-6 h-6 rounded-full bg-indigo-700 flex items-center justify-center text-xs font-bold">
          {number}
        </span>
        <span className="badge-blue capitalize text-xs">{exercise.type?.replace('_', ' ')}</span>
      </div>
      <p className="text-gray-300 font-medium mb-3">{exercise.instruction}</p>
      {isCorrect && exercise.content?.includes('___') ? (
        <p className="text-gray-100 mb-3 text-lg">
          {exercise.content.split('___')[0]}
          <span className="text-emerald-400 font-semibold bg-emerald-900/30 px-1 rounded">{userAnswer}</span>
          {exercise.content.split('___')[1]}
        </p>
      ) : (
        <p className="text-gray-100 mb-3 text-lg">{exercise.content}</p>
      )}

      {exercise.type === 'matching' && exercise.pairs ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-300">{exercise.instruction}</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-gray-400 mb-1">{t('lesson.leftColumn') || 'Kolumna lewa'}</p>
              {exercise.pairs.map((p, i) => (
                <div key={i} className="p-2 bg-gray-700 rounded mb-1 text-sm">{p.left}</div>
              ))}
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">{t('lesson.rightColumn') || 'Kolumna prawa'}</p>
              {exercise.pairs.map((p, i) => (
                <div key={i} className="p-2 bg-gray-800 rounded mb-1 text-sm">{p.right}</div>
              ))}
            </div>
          </div>
          {isAllRevealed && (
            <p className="text-xs text-emerald-400 mt-2">{t('lesson.correctMatches') || 'Poprawne pary'}: {exercise.answer}</p>
          )}
        </div>
      ) : exercise.type === 'error_correction' ? (
        <div className="space-y-3">
          <div className="p-3 bg-gray-900 rounded-lg border border-red-800/50">
            <p className="text-sm text-red-400 font-medium">{t('lesson.findError') || 'Znajdź błąd:'}</p>
            <p className="text-gray-100 mt-1">{exercise.content}</p>
          </div>
          <div>
            <label className="text-xs text-gray-400">{t('lesson.yourCorrection') || 'Twoja poprawka:'}</label>
            <input
              ref={inputRef}
              type="text"
              className={`input-field text-sm flex-1 ${checked ? (isCorrect ? 'border-emerald-500' : 'border-red-500') : ''}`}
              placeholder={t('lesson.correctSentence') || 'Poprawna zdania...'}
              value={userAnswer}
              onChange={e => { setUserAnswer(e.target.value); setChecked(false); setIsCorrect(null) }}
              onKeyDown={e => e.key === 'Enter' && !checked && handleCheck()}
              disabled={isAllRevealed}
            />
          </div>
          {checked && (
            <p className={`text-xs mt-1 font-medium ${isCorrect ? 'text-emerald-400' : 'text-red-400'}`}>
              {isCorrect ? '✓ Dobrze!' : `✗ Poprawnie: ${exercise.answer}`}
            </p>
          )}
          {isAllRevealed && exercise.explanation && (
            <p className="text-xs text-gray-400 mt-1 italic">{exercise.explanation}</p>
          )}
        </div>
      ) : exercise.type === 'multiple_choice' && exercise.options ? (
        <div className="space-y-2">
          {exercise.options.map((opt, i) => {
            const letter = opt.split('.')[0]?.trim()
            const isSelected = selectedOption === letter
            const isCorrect = isAllRevealed && letter === exercise.answer
            const isWrong = isAllRevealed && isSelected && letter !== exercise.answer
            return (
              <div
                key={i}
                className={`answer-option text-sm ${
                  isSelected ? 'selected' : ''
                } ${isCorrect ? 'correct' : ''} ${isWrong ? 'incorrect' : ''}`}
                onClick={() => !isAllRevealed && setSelectedOption(letter)}
              >
                <span>{opt}</span>
              </div>
            )
          })}
        </div>
      ) : (
        <div>
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              className={`input-field text-sm flex-1 ${checked ? (isCorrect ? 'border-emerald-500' : 'border-red-500') : ''}`}
              placeholder={t('lesson.yourAnswer')}
              value={userAnswer}
              onChange={e => { setUserAnswer(e.target.value); setChecked(false); setIsCorrect(null) }}
              onKeyDown={e => e.key === 'Enter' && !checked && handleCheck()}
              disabled={isAllRevealed}
            />
            {!isAllRevealed && !checked && (
              <button
                onClick={handleCheck}
                disabled={!userAnswer.trim()}
                className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-50 transition-colors"
              >
                Sprawdź
              </button>
            )}
          </div>
          {checked && (
            <p className={`text-xs mt-1 font-medium ${isCorrect ? 'text-emerald-400' : 'text-red-400'}`}>
              {isCorrect ? '✓ Dobrze!' : '✗ Nie do końca — sprawdź odpowiedź poniżej'}
            </p>
          )}
          {!isAllRevealed && (
            <SpecialChars
              language={language}
              inputRef={inputRef}
              value={userAnswer}
              onChange={(v) => { setUserAnswer(v); setChecked(false); setIsCorrect(null) }}
            />
          )}
        </div>
      )}

      <button
        className="text-indigo-400 hover:text-indigo-300 text-sm mt-3 flex items-center gap-1"
        onClick={handleRevealClick}
      >
        {revealBtnLabel}
      </button>
      {revealedCount > 0 && (
        <div className="mt-2 p-2 bg-emerald-900/20 border border-emerald-700/30 rounded text-sm text-emerald-300">
          {t('lesson.answerLabel')} {answerWords.slice(0, revealedCount).join(' ')}
          {!isAllRevealed && <span className="text-gray-500"> ...</span>}
        </div>
      )}
    </div>
  )
}
