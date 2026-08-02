import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Newspaper, BookOpen, ChevronDown, ChevronUp, ExternalLink, Plus, CheckCircle, Loader2 } from 'lucide-react'
import { getUserId, addFlashcard, addFlashcardAI, translateWord, getNews } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'
import PlayButton from '../components/PlayButton'

export default function News() {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState({})
  const [addedWords, setAddedWords] = useState({})
  const [activityDone, setActivityDone] = useState(false)
  const navigate = useNavigate()
  const userId = getUserId()
  const { t, targetLanguage } = useLanguage()

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    const today = new Date().toISOString().slice(0, 10)
    const cacheDateKey = `news_date_${userId}_${targetLanguage}`
    const cacheDataKey = `news_data_${userId}_${targetLanguage}`
    const cachedDate = localStorage.getItem(cacheDateKey)
    const cachedData = localStorage.getItem(cacheDataKey)
    const hasCached = cachedDate === today && cachedData

    if (hasCached) {
      try {
        setArticles(JSON.parse(cachedData))
        setLoading(false)
        return
      } catch (e) {
        // ignore parsing errors, will fetch fresh
      }
    }

    getNews(userId)
      .then(r => {
        const arts = r?.articles || []
        setArticles(arts)
        localStorage.setItem(cacheDateKey, today)
        localStorage.setItem(cacheDataKey, JSON.stringify(arts))
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [userId, targetLanguage])

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
    markTabComplete('news')
    setActivityDone(true)
  }

  const toggleArticle = (i) => setExpanded(prev => ({ ...prev, [i]: !prev[i] }))

  const handleAddFlashcard = async (word, translation, articleTitle) => {
    const key = `${word}-${translation}`
    if (addedWords[key]) return
    try {
      await addFlashcard(userId, {
        word,
        translation,
        example_sentence: `From article: ${articleTitle}`,
      })
      setAddedWords(prev => ({ ...prev, [key]: true }))
    } catch (e) {
      console.error('Failed to add flashcard:', e)
    }
  }

  if (loading) return <PageLoader text={t('news.loading')} />

  if (error) {
    return (
      <div className="page-container">
        <div className="card border-red-700/30 bg-red-900/10 text-center">
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="flex items-center gap-3 mb-6">
        <Newspaper className="w-7 h-7 text-blue-400" />
        <div>
          <h1 className="text-2xl font-bold">{t('news.title')}</h1>
          <p className="text-gray-400">{t('news.subtitle')}</p>
        </div>
      </div>

      {!activityDone ? (
        <button
          onClick={handleMarkDone}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700/30 hover:bg-emerald-700/50 border border-emerald-700/40 text-emerald-300 text-sm font-medium transition-colors mb-4"
        >
          <CheckCircle className="w-4 h-4" />
          Oznacz Newsy jako ukończone (+10 XP)
        </button>
      ) : (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-900/30 border border-emerald-700/40 text-emerald-400 text-sm font-medium mb-4">
          <CheckCircle className="w-4 h-4" />
          Newsy ukończone dziś ✓
        </div>
      )}

      {articles.length === 0 && (
        <div className="card text-center text-gray-400">
          {t('news.noArticles')}
        </div>
      )}

      <div className="space-y-4">
        {articles.map((article, i) => (
          <div key={i} className="card">
            {/* Article Header */}
            <button
              onClick={() => toggleArticle(i)}
              className="w-full flex items-start justify-between gap-3 text-left"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="badge-blue text-xs">{article.source || 'News'}</span>
                </div>
                <h2 className="font-semibold text-lg text-indigo-200">{article.title}</h2>
                {article.original_title && article.original_title !== article.title && (
                  <p className="text-gray-500 text-xs mt-0.5 italic">{article.original_title}</p>
                )}
              </div>
              {expanded[i]
                ? <ChevronUp className="w-5 h-5 text-gray-500 shrink-0 mt-1" />
                : <ChevronDown className="w-5 h-5 text-gray-500 shrink-0 mt-1" />
              }
            </button>

            {expanded[i] && (
              <div className="mt-4 pt-4 border-t border-gray-800 space-y-4">
                {/* Simplified Text */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-400 mb-2 flex items-center gap-1">
                    <BookOpen className="w-4 h-4" /> {t('news.simplified')}
                    <span className="text-xs text-gray-600 font-normal ml-1">· kliknij słowo → fiszka</span>
                  </h3>
                  <div className="flex items-start gap-2">
                    <ClickableText text={article.simplified_text} userId={userId} language={targetLanguage} />
                    <PlayButton text={article.simplified_text} language={targetLanguage} />
                  </div>
                </div>

                {/* Vocabulary */}
                {article.vocabulary?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-400 mb-2">{t('news.vocabulary')}</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {article.vocabulary.map((v, j) => {
                        const key = `${v.word}-${v.translation}`
                        return (
                          <div key={j} className="bg-gray-800 rounded-lg px-3 py-2 flex items-center justify-between gap-2">
                            <div>
                              <span className="text-indigo-300 font-medium">{v.word}</span>
                              <span className="text-gray-500 mx-2">→</span>
                              <span className="text-emerald-300">{v.translation}</span>
                              {v.cefr_level && (
                                <span className="ml-2 text-xs text-gray-600">{v.cefr_level}</span>
                              )}
                            </div>
                            <button
                              onClick={() => handleAddFlashcard(v.word, v.translation, article.title)}
                              className={`shrink-0 ${addedWords[key] ? 'text-emerald-500' : 'text-gray-600 hover:text-indigo-400'}`}
                              title={addedWords[key] ? t('news.addedToFlash') : t('news.addToFlash')}
                            >
                              {addedWords[key] ? '✓' : <Plus className="w-4 h-4" />}
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Comprehension Questions */}
                {article.comprehension_questions?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-400 mb-2">{t('news.comprehension')}</h3>
                    <div className="space-y-3">
                      {article.comprehension_questions.map((q, j) => (
                        <ComprehensionQuestion key={j} question={q.question} answer={q.answer} t={t} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Source Link */}
                {article.link && (
                  <a
                    href={article.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-sm"
                  >
                    <ExternalLink className="w-3 h-3" /> {t('news.readOriginal')}
                  </a>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function ClickableText({ text, userId, language }) {
  // Two-step flow: clicking a word SELECTS it (persistent green highlight) and
  // fetches its translation into a list at the bottom. Nothing is saved until
  // the learner presses "Dodaj zaznaczone" — then all selected words are added
  // to flashcards at once. Click a selected word again to deselect it.
  const [selected, setSelected] = useState({}) // clean -> { display, translation, loading }
  const [added, setAdded] = useState({})       // clean -> true (already saved this session)
  const [batchAdding, setBatchAdding] = useState(false)
  const [translations, setTranslations] = useState({})
  const [loadingTrans, setLoadingTrans] = useState({})

  const sentences = text
    ? text.match(/[^.!?]+[.!?]*/g)?.map(s => s.trim()).filter(Boolean) || [text]
    : []

  const cleanOf = w => w.replace(/[^a-zA-ZäöüßÄÖÜáéíóúñàâêîôùûçœ]/gi, '').toLowerCase()

  const toggleWord = async (token) => {
    const clean = cleanOf(token)
    if (!clean || clean.length < 2 || added[clean]) return
    if (selected[clean]) {
      setSelected(prev => { const n = { ...prev }; delete n[clean]; return n })
      return
    }
    setSelected(prev => ({ ...prev, [clean]: { display: clean, translation: '', loading: true } }))
    try {
      const res = await translateWord(clean, language, 'Polish', userId)
      setSelected(prev => prev[clean] ? { ...prev, [clean]: { ...prev[clean], translation: res.translation || '—', loading: false } } : prev)
    } catch {
      setSelected(prev => prev[clean] ? { ...prev, [clean]: { ...prev[clean], translation: '—', loading: false } } : prev)
    }
  }

  const removeSelected = (clean) => setSelected(prev => { const n = { ...prev }; delete n[clean]; return n })

  const addSelectedToFlashcards = async () => {
    const words = Object.keys(selected)
    if (!words.length) return
    setBatchAdding(true)
    for (const clean of words) {
      try {
        const tr = selected[clean].translation
        if (tr && tr !== '—') {
          await addFlashcard(userId, { word: clean, translation: tr, example_sentence: '' })
        } else {
          await addFlashcardAI(userId, clean)
        }
        setAdded(prev => ({ ...prev, [clean]: true }))
      } catch { /* skip the ones that fail; keep going */ }
    }
    setSelected({})
    setBatchAdding(false)
  }

  const handleTranslate = async (sentence, idx) => {
    if (translations[idx] || loadingTrans[idx]) return
    setLoadingTrans(prev => ({ ...prev, [idx]: true }))
    try {
      const res = await translateWord(sentence, language, 'Polish', userId)
      setTranslations(prev => ({ ...prev, [idx]: res.translation }))
    } catch {
      setTranslations(prev => ({ ...prev, [idx]: '—' }))
    } finally {
      setLoadingTrans(prev => ({ ...prev, [idx]: false }))
    }
  }

  const selectedList = Object.entries(selected)

  return (
    <div className="flex-1 leading-relaxed space-y-2 relative">
      {sentences.map((sentence, idx) => (
        <div key={idx}>
          <span>
            {sentence.split(/(\s+)/).map((token, ti) => {
              if (/^\s+$/.test(token)) return <span key={ti}>{token}</span>
              const clean = cleanOf(token)
              const isSel = !!selected[clean]
              const isAdded = !!added[clean]
              return (
                <span
                  key={ti}
                  onClick={() => toggleWord(token)}
                  className={`cursor-pointer rounded px-0.5 transition-colors ${
                    isAdded ? 'text-emerald-500 bg-emerald-900/30' :
                    isSel ? 'text-emerald-300 bg-emerald-800/40 ring-1 ring-emerald-600/50' :
                    'text-gray-200 hover:text-indigo-300 hover:bg-indigo-900/20'
                  }`}
                  title={isAdded ? 'Dodane do fiszek' : isSel ? 'Kliknij, aby odznaczyć' : 'Kliknij, aby zaznaczyć'}
                >
                  {token}
                </span>
              )
            })}
          </span>
          <button
            onClick={() => handleTranslate(sentence, idx)}
            disabled={!!loadingTrans[idx]}
            className="ml-1.5 text-xs text-gray-600 hover:text-indigo-400 transition-colors align-middle"
            title="Przetłumacz zdanie"
          >
            {loadingTrans[idx] ? '...' : translations[idx] ? '▲' : 'PL'}
          </button>
          {translations[idx] && (
            <p className="text-yellow-300/80 text-xs italic mt-0.5 ml-1">{translations[idx]}</p>
          )}
        </div>
      ))}

      {/* Selection basket — appears once at least one word is picked */}
      {selectedList.length > 0 && (
        <div className="mt-3 p-3 rounded-lg bg-gray-900/60 border border-emerald-800/40">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-emerald-300">Zaznaczone słowa ({selectedList.length})</span>
            <button onClick={() => setSelected({})} className="text-xs text-gray-500 hover:text-gray-300">Wyczyść</button>
          </div>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {selectedList.map(([clean, info]) => (
              <span key={clean} className="inline-flex items-center gap-1.5 bg-gray-800 border border-gray-700 rounded-full pl-2.5 pr-1 py-1 text-sm">
                <span className="text-emerald-200 font-medium">{info.display}</span>
                <span className="text-gray-500">→</span>
                <span className="text-gray-300">{info.loading ? '…' : info.translation}</span>
                <button onClick={() => removeSelected(clean)} className="ml-0.5 w-4 h-4 rounded-full hover:bg-gray-700 text-gray-500 hover:text-gray-200 text-xs flex items-center justify-center" title="Usuń">✕</button>
              </span>
            ))}
          </div>
          <button
            onClick={addSelectedToFlashcards}
            disabled={batchAdding}
            className="btn-primary text-sm flex items-center gap-2 disabled:opacity-50"
          >
            {batchAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Dodaj zaznaczone do fiszek ({selectedList.length})
          </button>
        </div>
      )}
    </div>
  )
}

function ComprehensionQuestion({ question, answer, t }) {
  const [showAnswer, setShowAnswer] = useState(false)
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <p className="text-gray-200 text-sm mb-2">{question}</p>
      <button
        onClick={() => setShowAnswer(s => !s)}
        className="text-indigo-400 hover:text-indigo-300 text-xs"
      >
        {showAnswer ? t('news.hideAnswer') : t('news.showAnswer')}
      </button>
      {showAnswer && (
        <p className="mt-2 text-emerald-300 text-sm">{answer}</p>
      )}
    </div>
  )
}
