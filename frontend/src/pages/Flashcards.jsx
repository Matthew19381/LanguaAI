import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Brain, ChevronLeft, ChevronRight, Download, Eye,
  CheckCircle, AlertCircle, Clock, Plus, CloudOff, UploadCloud
} from 'lucide-react'
import { getUserId, getFlashcards, getDueFlashcards, reviewFlashcard, exportAnki, addFlashcard, addFlashcardAI, bulkImportFlashcards, getFlashcardOfflinePack } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'
import { useOfflineSync } from '../hooks/useOfflineSync'
import { saveCardPack, loadCardPack, enqueueFlashcardReview } from '../utils/offlineQueue'
import PlayButton from '../components/PlayButton'

// German gender colors
const GENDER_COLORS = {
  der: { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/30', label: 'm.' },
  die: { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/30', label: 'f.' },
  das: { bg: 'bg-green-500/20', text: 'text-green-300', border: 'border-green-500/30', label: 'n.' },
};

function GenderBadge({ gender }) {
  if (!gender || !GENDER_COLORS[gender]) return null;
  const c = GENDER_COLORS[gender];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-sm font-medium ${c.bg} ${c.text} border ${c.border} mr-2`}>
      {gender}
    </span>
  );
}

function highlightWordInSentence(sentence, word, gender, isImportant = false) {
  if (!sentence || !word) return sentence;
  const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`\\b(${escaped})\\b`, 'gi');

  // Get gender color class
  let genderColorClass = '';
  if (gender && GENDER_COLORS[gender]) {
    genderColorClass = GENDER_COLORS[gender].bg.replace('/20', '/40');
  }

  // Get importance color class (yellow for important words)
  let importanceColorClass = '';
  if (isImportant) {
    importanceColorClass = 'bg-yellow-500/30';
  }

  // Combine classes: if both exist, use gender color (as requested)
  // If only one exists, use that one
  // If neither exists, use default yellow
  let finalColorClass = '';
  if (genderColorClass && importanceColorClass) {
    // Both present - use gender color as requested
    finalColorClass = genderColorClass;
  } else if (genderColorClass) {
    // Only gender color
    finalColorClass = genderColorClass;
  } else if (importanceColorClass) {
    // Only importance color
    finalColorClass = importanceColorClass;
  } else {
    // Neither - default to yellow
    finalColorClass = 'bg-yellow-500/30';
  }

  return sentence.replace(regex, `<mark class="${finalColorClass} rounded px-0.5">\$1</mark>`);
}

const TABS = { ALL: 'all', DUE: 'due' }

export default function Flashcards() {
  const [tab, setTab] = useState(TABS.DUE)
  const [allCards, setAllCards] = useState([])
  const [dueCards, setDueCards] = useState([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isFlipped, setIsFlipped] = useState(false)
  const [reviewDone, setReviewDone] = useState(new Set())
  const [dateFilter, setDateFilter] = useState('all') // 'all', 'today', 'week', 'month'
  const [lessonFilter, setLessonFilter] = useState('all') // 'all' or lesson_day number
  const [cefrFilter, setCefrFilter] = useState('all') // 'all', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'
  const [offlineMode, setOfflineMode] = useState(false)
  const [packMsg, setPackMsg] = useState('')
  const navigate = useNavigate()
  const userId = getUserId()
  const { t, targetLanguage } = useLanguage()
  const { pending, refresh: refreshPending } = useOfflineSync()

  const [showAddForm, setShowAddForm] = useState(true)

  // Add card form
  const [newWord, setNewWord] = useState('')
  const [newTranslation, setNewTranslation] = useState('')
  const [newExample, setNewExample] = useState('')
  const [addMsg, setAddMsg] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiPreview, setAiPreview] = useState(null)
  const [reversed, setReversed] = useState(false) // PL→target instead of target→PL
  const [exportError, setExportError] = useState('')
  const [addLoading, setAddLoading] = useState(false)
  const [allTotal, setAllTotal] = useState(0)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 50

  // Bulk import
  const [showImport, setShowImport] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    loadCards()
  }, [userId])

  const loadCards = async (p = page) => {
    setLoading(true)
    try {
      const [all, due] = await Promise.all([
        getFlashcards(userId, { limit: PAGE_SIZE, offset: p * PAGE_SIZE }),
        getDueFlashcards(userId)
      ])
      setAllCards(all.flashcards || [])
      setAllTotal(all.total || 0)
      setDueCards(due.due_cards || [])
      setOfflineMode(false)
      // Keep a pack on the device for the next time there is no network
      getFlashcardOfflinePack(userId).then(saveCardPack).catch(() => {})
    } catch (e) {
      // No network: fall back to the downloaded pack so review still works
      const pack = loadCardPack()
      if (pack?.flashcards?.length) {
        const now = Date.now()
        const due = pack.flashcards.filter(
          c => !c.next_review_date || new Date(c.next_review_date).getTime() <= now
        )
        setAllCards(pack.flashcards)
        setAllTotal(pack.flashcards.length)
        setDueCards(due)
        setOfflineMode(true)
      }
    }
    finally { setLoading(false) }
  }

  const handleDownloadCardPack = async () => {
    try {
      const pack = await getFlashcardOfflinePack(userId)
      setPackMsg(saveCardPack(pack)
        ? t('flash.packSaved').replace('{n}', pack.flashcards.length)
        : t('flash.packFailed'))
    } catch {
      setPackMsg(t('flash.packFailed'))
    }
  }

  const filterCards = (cards) => {
    if (tab === TABS.DUE) return cards
    const now = new Date()
    return cards.filter(c => {
      // Date filter
      if (dateFilter !== 'all') {
        if (!c.created_at) return true
        const created = new Date(c.created_at)
        if (dateFilter === 'today' && created.toDateString() !== now.toDateString()) return false
        if (dateFilter === 'week' && (now - created) > 7 * 24 * 60 * 60 * 1000) return false
        if (dateFilter === 'month' && (now - created) > 30 * 24 * 60 * 60 * 1000) return false
      }
      // Lesson day filter
      if (lessonFilter !== 'all' && c.lesson_day !== parseInt(lessonFilter)) return false
      // CEFR level filter
      if (cefrFilter !== 'all' && c.cefr_level !== cefrFilter) return false
      return true
    })
  }
  const displayCards = filterCards(tab === TABS.DUE ? dueCards : allCards)
  const currentCard = displayCards[currentIndex]

  // Use refs to avoid stale closures in keyboard handler
  const stateRef = useRef({ currentCard, isFlipped, currentIndex, displayCards, tab })
  useEffect(() => {
    stateRef.current = { currentCard, isFlipped, currentIndex, displayCards, tab }
  }, [currentCard, isFlipped, currentIndex, displayCards, tab])

  const handleFlip = useCallback(() => {
    const { isFlipped: flipped } = stateRef.current
    setIsFlipped(!flipped)
  }, [])

  const handleNext = useCallback(() => {
    setIsFlipped(false)
    setCurrentIndex(i => {
      const maxIdx = stateRef.current.displayCards.length - 1
      return Math.min(i + 1, maxIdx)
    })
  }, [])

  const handlePrev = useCallback(() => {
    setIsFlipped(false)
    setCurrentIndex(i => Math.max(0, i - 1))
  }, [])

  const handleReview = useCallback(async (rating) => {
    const { currentCard: card, currentIndex: idx, displayCards: cards } = stateRef.current
    if (!card) return
    const advance = () => {
      setReviewDone(prev => new Set([...prev, card.id]))
      if (idx < cards.length - 1) {
        setIsFlipped(false)
        setCurrentIndex(i => Math.min(i + 1, cards.length - 1))
      }
    }
    // Offline (or the connection drops mid-session): queue the rating and move
    // on. Flashcards are self-rated, so nothing needs grading on the device.
    const queueIt = () => {
      enqueueFlashcardReview({ flashcardId: card.id, userId, rating })
      refreshPending()
      advance()
    }
    if (!navigator.onLine) { queueIt(); return }
    try {
      await reviewFlashcard(card.id, rating, userId)
      advance()
    } catch (e) {
      queueIt()
    }
  }, [userId])

  // Keyboard navigation: Space/Enter = flip, 1-4 = review rating, ←/→ = prev/next
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      const { currentCard: card } = stateRef.current
      if (!card) return
      if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); handleFlip() }
      else if (e.key === 'ArrowRight') handleNext()
      else if (e.key === 'ArrowLeft') handlePrev()
      else if (e.key === '1') handleReview(1)
      else if (e.key === '2') handleReview(2)
      else if (e.key === '3') handleReview(3)
      else if (e.key === '4') handleReview(4)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [handleFlip, handleNext, handlePrev, handleReview])

  const handleExport = async () => {
    setExporting(true)
    try {
      const response = await exportAnki(userId)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'flashcards.apkg')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      setExportError('Export failed: ' + e.message)
      setTimeout(() => setExportError(''), 4000)
    } finally {
      setExporting(false)
    }
  }

  const handleAddCard = async () => {
    if (!newWord || !newTranslation || addLoading) return
    setAddLoading(true)
    setAddMsg('')
    try {
      const res = await addFlashcard(userId, {
        word: newWord,
        translation: newTranslation,
        example_sentence: newExample
      })
      if (res.success) {
        setAddMsg(t('flash.cardAdded') || 'Card added successfully!')
        setNewWord('')
        setNewTranslation('')
        setNewExample('')
        loadCards()
      } else {
        setAddMsg(res.message || t('flash.cardExists'))
      }
    } catch (e) {
      setAddMsg('Error: ' + e.message)
    } finally {
      setAddLoading(false)
    }
  }

  const handleBulkImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setImportResult(null)
    try {
      const res = await bulkImportFlashcards(userId, file)
      setImportResult(res)
      loadCards()
    } catch (err) {
      setImportResult({ success: false, message: err.message || 'Import failed' })
    } finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  if (loading) return <PageLoader text={t('flash.loading')} />

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Brain className="w-7 h-7 text-purple-400" />
          <div>
            <h1 className="text-2xl font-bold">{t('flash.title')}</h1>
            <p className="text-gray-400 text-sm">
              {allCards.length} {t('flash.total')} · {dueCards.length} {t('flash.dueToday')}
            </p>
          </div>
        </div>
        <button
          className="btn-secondary flex items-center gap-2 text-sm"
          onClick={handleExport}
          disabled={exporting || allCards.length === 0}
        >
          <Download className="w-4 h-4" />
          {exporting ? t('flash.exporting') : t('flash.exportAnki')}
        </button>
        {exportError && (
          <span className="text-red-400 text-sm flex items-center gap-1">
            <AlertCircle className="w-4 h-4" /> {exportError}
          </span>
        )}
      </div>

      {/* Offline status + pack download */}
      <div className="flex flex-wrap items-center gap-2 mb-4 text-xs">
        {offlineMode && (
          <span className="px-2.5 py-1 rounded-lg bg-amber-900/40 text-amber-200 flex items-center gap-1">
            <CloudOff className="w-3 h-3" /> {t('flash.offlineMode')}
          </span>
        )}
        {pending > 0 && (
          <span className="px-2.5 py-1 rounded-lg bg-sky-900/40 text-sky-200 flex items-center gap-1">
            <UploadCloud className="w-3 h-3" /> {t('practice.pending').replace('{n}', pending)}
          </span>
        )}
        <button
          onClick={handleDownloadCardPack}
          disabled={offlineMode}
          className="px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-40 flex items-center gap-1 transition-colors"
        >
          <Download className="w-3 h-3" /> {t('flash.downloadPack')}
        </button>
        {packMsg && <span className="text-gray-400">{packMsg}</span>}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-4">
        {[
          { key: TABS.DUE, label: `${t('flash.dueTab')} (${dueCards.length})`, icon: <Clock className="w-4 h-4" /> },
          { key: TABS.ALL, label: `${t('flash.allTab')} (${allCards.length})`, icon: <Eye className="w-4 h-4" /> },
        ].map(({ key, label, icon }) => (
          <button
            key={key}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === key
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-gray-100'
            }`}
            onClick={() => { setTab(key); setCurrentIndex(0); setIsFlipped(false); if (key === TABS.ALL) { setPage(0); loadCards(0); } }}
          >
            {icon}{label}
          </button>
        ))}
        <button
          onClick={() => setShowAddForm(s => !s)}
          className={`ml-auto flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${showAddForm ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-100'}`}
        >
          <Plus className="w-4 h-4" />{t('flash.addTab')}
        </button>
        <button
          onClick={() => setShowImport(s => !s)}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${showImport ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-100'}`}
        >
          <Download className="w-4 h-4" />{t('flash.importTab') || 'Import'}
        </button>
      </div>

      {/* Flashcard Viewer */}
      {(tab === TABS.ALL || tab === TABS.DUE) && (
        <>
          {tab === TABS.ALL && (
            <div className="mb-4 space-y-2">
              <div className="flex gap-2 flex-wrap">
                <span className="text-gray-500 text-sm self-center">Data:</span>
                {[
                  { key: 'all', label: 'Wszystkie' },
                  { key: 'today', label: 'Dzisiaj' },
                  { key: 'week', label: 'Ten tydzień' },
                  { key: 'month', label: 'Ten miesiąc' },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => { setDateFilter(key); setCurrentIndex(0) }}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      dateFilter === key ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {/* Lesson day filter */}
              {(() => {
                const days = [...new Set(allCards.filter(c => c.lesson_day).map(c => c.lesson_day))].sort((a, b) => a - b)
                if (days.length === 0) return null
                return (
                  <div className="flex gap-2 flex-wrap">
                    <span className="text-gray-500 text-sm self-center">Lekcja:</span>
                    <button
                      onClick={() => { setLessonFilter('all'); setCurrentIndex(0) }}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${lessonFilter === 'all' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'}`}
                    >Wszystkie</button>
                    {days.map(day => (
                      <button
                        key={day}
                        onClick={() => { setLessonFilter(String(day)); setCurrentIndex(0) }}
                        className={`px-3 py-1 rounded text-xs font-medium transition-colors ${lessonFilter === String(day) ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'}`}
                      >
                        Dzień {day}
                      </button>
                    ))}
                  </div>
                )
              })()}

                {/* CEFR level filter */}
                <div className="flex gap-2 flex-wrap">
                  <span className="text-gray-500 text-sm self-center">Poziom:</span>
                  <button
                    onClick={() => { setCefrFilter("all"); setCurrentIndex(0) }}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${cefrFilter === "all" ? "bg-purple-600 text-white" : "bg-gray-800 text-gray-400 hover:text-gray-200"}`}
                  >Wszystkie</button>
                  {["A1", "A2", "B1", "B2", "C1", "C2"].map(level => (
                    <button
                      key={level}
                      onClick={() => { setCefrFilter(level); setCurrentIndex(0) }}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${cefrFilter === level ? "bg-purple-600 text-white" : "bg-gray-800 text-gray-400 hover:text-gray-200"}`}
                    >{level}</button>
                  ))}
                </div>
            </div>
          )}
          {displayCards.length === 0 ? (
            <div className="card text-center py-12">
              {tab === TABS.DUE ? (
                <>
                  <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold mb-1">{t('flash.allCaughtUp')}</h3>
                  <p className="text-gray-400">{t('flash.noDueCards')}</p>
                </>
              ) : (
                <>
                  <Brain className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold mb-1">{t('flash.noCards')}</h3>
                  <p className="text-gray-400">{t('flash.completeLesson')}</p>
                </>
              )}
            </div>
          ) : (
            <div className="max-w-lg mx-auto">
              {/* Card counter */}
              <div className="flex justify-between text-sm text-gray-400 mb-3">
                <span>{currentIndex + 1} / {displayCards.length}</span>
                <div className="flex items-center gap-3">
                  {tab === TABS.DUE && (
                    <span>{reviewDone.size} {t('flash.reviewed')}</span>
                  )}
                  <button
                    onClick={() => { setReversed(r => !r); setIsFlipped(false) }}
                    className={`text-xs px-2 py-0.5 rounded transition-colors ${reversed ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'}`}
                    title="Odwróć kierunek fiszek"
                  >
                    {reversed ? 'PL → cel' : 'cel → PL'}
                  </button>
                </div>
              </div>

              {/* Flashcard */}
              {currentCard && (
                <div className="flashcard-container mb-6">
                  <div
                    className={`flashcard ${isFlipped ? 'flipped' : ''}`}
                    onClick={handleFlip}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleFlip() } }}
                    tabIndex={0}
                    role="button"
                    aria-label={isFlipped ? (t('flash.showFront') || 'Pokaż przód') : (t('flash.reveal') || 'Odpowiedź')}
                    aria-expanded={isFlipped}
                  >
                    {/* Front */}
                    <div className="flashcard-front">
                      <div className="text-center">
                        <p className="text-gray-400 text-xs mb-2 uppercase tracking-wider">
                          {reversed ? 'Polski' : t('flash.wordSide')}
                        </p>
                        {reversed ? (
                          <p className="text-3xl font-bold text-emerald-300">{currentCard.translation}</p>
                        ) : (
                          <div className="flex items-center justify-center gap-2">
                            <GenderBadge gender={currentCard.gender} />
                            <p className="text-3xl font-bold text-indigo-300">{currentCard.word}</p>
                            <div onClick={e => e.stopPropagation()}>
                              <PlayButton text={currentCard.word} language={currentCard.language || targetLanguage} />
                            </div>
                          </div>
                        )}
                        <p className="text-gray-500 text-xs mt-3">{t('flash.clickReveal')}</p>
                      </div>
                    </div>
                    {/* Back */}
                    <div className="flashcard-back">
                      <div className="text-center">
                        <p className="text-gray-400 text-xs mb-2 uppercase tracking-wider">
                          {reversed ? t('flash.wordSide') : t('flash.translationSide')}
                        </p>
                        {reversed ? (
                          <div className="flex items-center justify-center gap-2 mb-1">
                            <GenderBadge gender={currentCard.gender} />
                            <p className="text-3xl font-bold text-indigo-300">{currentCard.word}</p>
                            <div onClick={e => e.stopPropagation()}>
                              <PlayButton text={currentCard.word} language={currentCard.language || targetLanguage} />
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className="flex items-center justify-center gap-2 mb-1">
                              <GenderBadge gender={currentCard.gender} />
                              <p className="text-3xl font-bold text-indigo-300">{currentCard.word}</p>
                              <div onClick={e => e.stopPropagation()}>
                                <PlayButton text={currentCard.word} language={currentCard.language || targetLanguage} />
                              </div>
                            </div>
                            <p className="text-2xl font-bold text-emerald-300">{currentCard.translation}</p>
                          </>
                        )}
                        {currentCard.example_sentence && (
                                                                          <p
                                                                            className="text-gray-400 text-sm mt-3 italic max-w-xs"
                                                                            dangerouslySetInnerHTML={{ __html: highlightWordInSentence(currentCard.example_sentence, currentCard.word, currentCard.gender, currentCard.isImportant) }}
                                                                          ></p>
                                                                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Review buttons (only for due tab) */}
              {tab === TABS.DUE && isFlipped && currentCard && (
                <div className="grid grid-cols-4 gap-2 mb-4">
                  {[
                    { rating: 1, labelKey: 'flash.again', color: 'bg-red-700 hover:bg-red-600 text-white', desc: '<1d', ariaKey: 'flash.again' },
                    { rating: 2, labelKey: 'flash.hard', color: 'bg-orange-700 hover:bg-orange-600 text-white', desc: '~3d', ariaKey: 'flash.hard' },
                    { rating: 3, labelKey: 'flash.good', color: 'bg-blue-700 hover:bg-blue-600 text-white', desc: '~7d', ariaKey: 'flash.good' },
                    { rating: 4, labelKey: 'flash.easy', color: 'bg-emerald-700 hover:bg-emerald-600 text-white', desc: '~14d', ariaKey: 'flash.easy' },
                  ].map(({ rating, labelKey, color, desc, ariaKey }) => (
                    <button
                      key={rating}
                      className={`${color} rounded-lg py-2 text-sm font-medium transition-colors`}
                      onClick={() => handleReview(rating)}
                      aria-label={`${t(ariaKey)} — ${desc}`}
                    >
                      <div>{t(labelKey)}</div>
                      <div className="text-xs opacity-75">{desc}</div>
                    </button>
                  ))}
                </div>
              )}

              {/* Navigation */}
              <div className="flex justify-between" role="group" aria-label={t('flash.cardNav') || 'Nawigacja fiszek'}>
                <button
                  className="btn-secondary flex items-center gap-2"
                  onClick={handlePrev}
                  disabled={currentIndex === 0}
                  aria-label={t('flash.previous') || 'Poprzednia fiszka'}
                >
                  <ChevronLeft className="w-4 h-4" />
                  {t('flash.previous')}
                </button>
                <button
                  className={isFlipped ? 'btn-primary' : 'btn-secondary'}
                  onClick={handleFlip}
                  aria-label={isFlipped ? (t('flash.showFront') || 'Pokaż przód') : (t('flash.reveal') || 'Odpowiedź')}
                >
                  {isFlipped ? t('flash.showFront') : t('flash.reveal')}
                </button>
                <button
                  className="btn-secondary flex items-center gap-2"
                  onClick={handleNext}
                  disabled={currentIndex === displayCards.length - 1}
                  aria-label={t('flash.next') || 'Następna fiszka'}
                >
                  {t('flash.next')}
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              {/* Progress dots */}
              <div className="flex gap-1.5 mt-4 justify-center flex-wrap" role="tablist" aria-label={t('flash.cardProgress') || 'Postęp fiszek'}>
                {displayCards.map((card, i) => (
                  <button
                    key={i}
                    className={`w-2 h-2 rounded-full transition-all ${
                      i === currentIndex
                        ? 'bg-indigo-400 w-4'
                        : reviewDone.has(card.id)
                        ? 'bg-emerald-600'
                        : 'bg-gray-700'
                    }`}
                    onClick={() => { setCurrentIndex(i); setIsFlipped(false) }}
                    role="tab"
                    aria-selected={i === currentIndex}
                    aria-label={`${t('flash.card') || 'Fiszka'} ${i + 1}${reviewDone.has(card.id) ? ` (${t('flash.reviewed') || 'przejrzana'})` : ''}`}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Pagination (All tab only, server-side) */}
          {tab === TABS.ALL && allTotal > PAGE_SIZE && (
            <div className="flex items-center justify-center gap-3 mt-4">
              <button
                className="btn-secondary text-sm px-3 py-1.5 disabled:opacity-40"
                disabled={page === 0}
                onClick={() => { const p = page - 1; setPage(p); setCurrentIndex(0); loadCards(p) }}
              >
                ← {t('flash.prevPage') || 'Poprzednia'}
              </button>
              <span className="text-gray-400 text-sm">
                {t('flash.page') || 'Strona'} {page + 1} / {Math.ceil(allTotal / PAGE_SIZE)}
                <span className="text-gray-600 ml-2">({allTotal} {t('flash.total') || 'łącznie'})</span>
              </span>
              <button
                className="btn-secondary text-sm px-3 py-1.5 disabled:opacity-40"
                disabled={(page + 1) * PAGE_SIZE >= allTotal}
                onClick={() => { const p = page + 1; setPage(p); setCurrentIndex(0); loadCards(p) }}
              >
                {t('flash.nextPage') || 'Następna'} →
              </button>
            </div>
          )}
        </>
      )}

      {/* Add Card Panel */}
      {showAddForm && (
        <div className="card mt-6 max-w-lg">
          <h2 className="text-xl font-semibold mb-2">{t('flash.addNew')}</h2>
          <p className="text-gray-500 text-sm mb-4">Wpisz słowo — AI automatycznie doda tłumaczenie i przykład.</p>
          {addMsg && (
            <div className={`p-3 rounded-lg mb-4 text-sm ${
              addMsg.includes('successfully') || addMsg.includes('dodana') || addMsg.includes('AI')
                ? 'bg-emerald-900/30 text-emerald-300'
                : 'bg-yellow-900/30 text-yellow-300'
            }`}>
              {addMsg}
            </div>
          )}
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">{t('flash.wordPhrase')}</label>
              <input
                className="input-field"
                placeholder={t('flash.wordPlaceholder')}
                value={newWord}
                onChange={e => { setNewWord(e.target.value); setAiPreview(null) }}
              />
            </div>

            {aiPreview && (
              <div className="bg-gray-800 rounded-lg p-3 border border-indigo-700/40">
                <p className="text-xs text-gray-500 mb-2">Podgląd fiszki (wygenerowane przez AI):</p>
                <div className="space-y-1 text-sm">
                  <p><span className="text-gray-500">Słowo:</span> <span className="text-indigo-300 font-medium">{newWord}</span></p>
                  <p><span className="text-gray-500">Tłumaczenie:</span> <span className="text-emerald-300">{aiPreview.translation || '(brak)'}</span></p>
                  <p><span className="text-gray-500">Przykład:</span> <span className="text-gray-300 italic">{aiPreview.example || '(brak)'}</span></p>
                </div>
              </div>
            )}

            {!aiPreview ? (
              <button
                className="btn-primary w-full flex items-center justify-center gap-2"
                onClick={async () => {
                  if (!newWord.trim()) return
                  setAiLoading(true)
                  setAddMsg('')
                  try {
                    const res = await addFlashcardAI(userId, newWord.trim())
                    if (res.success) {
                      setAiPreview({ translation: res.translation, example: res.example })
                      setAddMsg('AI wygenerowało fiszkę. Sprawdź podgląd poniżej.')
                    } else {
                      setAddMsg(res.message || t('flash.cardExists'))
                      setNewWord('')
                    }
                  } catch (e) {
                    setAddMsg('Błąd: ' + e.message)
                  } finally {
                    setAiLoading(false)
                  }
                }}
                disabled={!newWord.trim() || aiLoading}
              >
                {aiLoading ? <><Plus className="w-4 h-4 animate-spin" /> Generowanie AI...</> : <><Plus className="w-4 h-4" /> Dodaj z AI</>}
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  className="btn-primary flex-1"
                  onClick={() => {
                    setAddMsg('Fiszka dodana! ✓')
                    setNewWord('')
                    setAiPreview(null)
                    loadCards()
                  }}
                >
                  Zapisz fiszkę
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => { setAiPreview(null); setAddMsg('') }}
                >
                  Anuluj
                </button>
              </div>
            )}

            <div className="border-t border-gray-700 pt-3">
              <p className="text-xs text-gray-600 mb-2">Lub dodaj ręcznie:</p>
              <div className="space-y-2">
                <input
                  className="input-field text-sm"
                  placeholder={t('flash.translationPlaceholder')}
                  value={newTranslation}
                  onChange={e => setNewTranslation(e.target.value)}
                />
                <input
                  className="input-field text-sm"
                  placeholder={t('flash.examplePlaceholder')}
                  value={newExample}
                  onChange={e => setNewExample(e.target.value)}
                />
                <button
                  className="btn-secondary w-full text-sm"
                  onClick={handleAddCard}
                  disabled={!newWord || !newTranslation || addLoading}
                >
                  {addLoading ? t('flash.adding') || 'Dodawanie...' : t('flash.addButton')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Import Panel */}
      {showImport && (
        <div className="card mt-6 max-w-lg">
          <h2 className="text-xl font-semibold mb-2">{t('flash.bulkImport') || 'Import z pliku'}</h2>
          <p className="text-gray-500 text-sm mb-4">
            {t('flash.bulkImportDesc') || 'Zaimportuj fiszki z pliku CSV lub TSV. Kolumny: word, translation, example (opcjonalne).'}
          </p>
          {importResult && (
            <div className={`p-3 rounded-lg mb-4 text-sm ${
              importResult.success ? 'bg-emerald-900/30 text-emerald-300' : 'bg-red-900/30 text-red-300'
            }`}>
              {importResult.message || importResult}
              {importResult.errors?.length > 0 && (
                <ul className="mt-2 text-xs list-disc list-inside">
                  {importResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                </ul>
              )}
            </div>
          )}
          <div className="space-y-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.tsv,.txt"
              onChange={handleBulkImport}
              disabled={importing}
              className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 file:cursor-pointer disabled:opacity-50"
            />
            {importing && <p className="text-gray-400 text-sm">{t('flash.importing') || 'Importowanie...'}</p>}
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">{t('flash.csvExample') || 'Przykład CSV:'}</p>
              <pre className="text-xs text-gray-400 font-mono">word,translation,example
Haus,dom,Das Haus ist groß
Katze,die Katze,Meine Katze schläft</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
