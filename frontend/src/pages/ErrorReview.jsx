import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronDown, ChevronUp, BookOpen, Brain, FlaskConical, MessageSquare } from 'lucide-react'
import { getUserId, getAllErrors, addFlashcardAI, getTestFromErrors, askQuestion } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import PlayButton from '../components/PlayButton'
import { useLanguage } from '../hooks/useLanguage'

const CATEGORY_LABELS = {
  grammar: 'Gramatyka',
  vocabulary: 'Słownictwo',
  word_order: 'Szyk zdania',
  articles: 'Rodzajniki',
  verb_conjugation: 'Koniugacja',
  prepositions: 'Przyimki',
  spelling: 'Pisownia',
  pronunciation: 'Wymowa',
  case: 'Przypadki',
  comprehension: 'Rozumienie',
  syntax: 'Składnia',
  pronunciation_spelling: 'Wymowa/Pisownia',
  fluency: 'Płynność',
  register: 'Rejestr',
  application: 'Zastosowanie',
  unknown: 'Inne',
}

export default function ErrorReview() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState({})
  const [practiceState, setPracticeState] = useState({})
  const [flashMsg, setFlashMsg] = useState('')
  const [flashLoading, setFlashLoading] = useState(false)
  const [testLoading, setTestLoading] = useState(false)
  const [voiceChatText, setvoiceChatText] = useState('')
  const [voiceChatAnalysis, setvoiceChatAnalysis] = useState('')
  const [voiceChatLoading, setvoiceChatLoading] = useState(false)
  const navigate = useNavigate()
  const userId = getUserId()
  const { targetLanguage } = useLanguage()

  const handleGenerateFlashcards = async () => {
    if (!data?.groups || !userId) return
    setFlashLoading(true)
    setFlashMsg('')
    const allErrors = data.groups.flatMap(g => g.errors)
    const unique = [...new Set(allErrors.map(e => e.correct_answer).filter(Boolean))]
    let added = 0
    for (const word of unique.slice(0, 20)) {
      try {
        const res = await addFlashcardAI(userId, word)
        if (res.success) added++
      } catch {}
    }
    setFlashMsg(`Dodano ${added} fiszek z błędów.`)
    setFlashLoading(false)
  }

  const handleGenerateTest = async () => {
    if (!userId) return
    setTestLoading(true)
    try {
      const test = await getTestFromErrors(userId)
      const today = new Date().toISOString().slice(0, 10)
      const lang = localStorage.getItem('userLanguage') || ''
      localStorage.setItem(`test_cache_${userId}_${lang}_${today}`, JSON.stringify(test))
      navigate('/test')
    } catch (e) {
      setFlashMsg('Błąd generowania testu.')
    } finally {
      setTestLoading(false)
    }
  }

  const handlevoiceChatAnalysis = async () => {
    if (!voiceChatText.trim() || !userId) return
    setvoiceChatLoading(true)
    setvoiceChatAnalysis('')
    try {
      const lang = data?.language || targetLanguage || 'English'
      const prompt = `Przeanalizuj poniższe podsumowanie rozmowy w języku ${lang}. Oceń:
1. Wymowę/pisownię (błędy ortograficzne lub wymowa opisana w tekście)
2. Gramatykę (błędne formy, koniugacje, deklinacje)
3. Słownictwo (czy dobór słów jest właściwy)
4. Płynność i naturalność wypowiedzi

Podaj konkretne błędy z korektą i ogólną ocenę (A/B/C). Odpowiedź po polsku.

Podsumowanie rozmowy:
${voiceChatText.trim()}`
      const res = await askQuestion(prompt, userId)
      setvoiceChatAnalysis(res.answer || 'Brak analizy.')
    } catch {
      setvoiceChatAnalysis('Błąd analizy.')
    } finally {
      setvoiceChatLoading(false)
    }
  }

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    getAllErrors(userId)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [userId])

  const toggleGroup = (type) => setExpanded(prev => ({ ...prev, [type]: !prev[type] }))

  if (loading) return <PageLoader text="Ładowanie błędów..." />
  if (!data) return null

  return (
    <div className="page-container max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <AlertTriangle className="w-7 h-7 text-yellow-400" />
        <div>
          <h1 className="text-2xl font-bold">Przegląd błędów</h1>
          <p className="text-gray-400">
            {data.total} błędów łącznie · {data.language}
          </p>
        </div>
      </div>

      {data.total > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={handleGenerateFlashcards}
            disabled={flashLoading || testLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-700/30 hover:bg-purple-700/50 border border-purple-700/40 text-purple-300 text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Brain className="w-4 h-4" />
            {flashLoading ? 'Generowanie...' : 'Generuj fiszki z błędów'}
          </button>
          <button
            onClick={handleGenerateTest}
            disabled={flashLoading || testLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-700/30 hover:bg-indigo-700/50 border border-indigo-700/40 text-indigo-300 text-sm font-medium transition-colors disabled:opacity-50"
          >
            <FlaskConical className="w-4 h-4" />
            {testLoading ? 'Generowanie...' : 'Generuj test z błędów'}
          </button>
          {flashMsg && <span className="text-sm text-emerald-400 self-center">{flashMsg}</span>}
        </div>
      )}

      {data.total === 0 ? (
        <div className="card text-center py-12">
          <BookOpen className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <p className="text-emerald-300 font-semibold text-lg">Brak błędów!</p>
          <p className="text-gray-500 text-sm mt-1">Zrób kilka testów, żeby zobaczyć swoje błędy tutaj.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.groups.map(group => (
            <div key={group.type} className="card">
              <button
                className="w-full flex items-center justify-between"
                onClick={() => toggleGroup(group.type)}
              >
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-red-900/50 border border-red-700/40 flex items-center justify-center text-sm font-bold text-red-300">
                    {group.count}
                  </span>
                  <span className="font-semibold text-gray-200">
                    {CATEGORY_LABELS[group.type] || group.type}
                  </span>
                </div>
                {expanded[group.type]
                  ? <ChevronUp className="w-4 h-4 text-gray-500" />
                  : <ChevronDown className="w-4 h-4 text-gray-500" />
                }
              </button>

              {expanded[group.type] && (
                <div className="mt-4 space-y-3">
                  {group.errors.map((err, i) => (
                    <div key={i} className="bg-gray-800/60 rounded-lg p-3 border border-gray-700/40">
                      {/* Source tag + date */}
                      <div className="flex items-center gap-2 mb-1">
                        {err.source === 'conversation' && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-900/40 border border-indigo-700/40 text-indigo-400">Rozmowa</span>
                        )}
                        <span className="text-xs text-gray-600 ml-auto">{err.date}</span>
                      </div>
                      {/* Question */}
                      {err.question && (
                        <p className="text-gray-300 text-xs mb-2 font-medium">{err.question}</p>
                      )}
                      {/* User answer â†’ Correct answer */}
                      <div className="flex items-center gap-3 flex-wrap mb-2">
                        <div>
                          <span className="text-gray-500 text-xs">Twoja odpowiedź: </span>
                          <span className="text-red-400 font-medium text-sm line-through">{err.user_answer || 'â€”'}</span>
                        </div>
                        <span className="text-gray-600">â†’</span>
                        <div className="flex items-center gap-1">
                          <span className="text-gray-500 text-xs">Poprawna: </span>
                          <span className="text-emerald-400 font-medium text-sm">{err.correct_answer}</span>
                          {err.correct_answer && <PlayButton text={err.correct_answer} language={data.language} />}
                        </div>
                      </div>

                      {err.explanation && (
                        <p className="text-gray-400 text-xs leading-relaxed">{err.explanation}</p>
                      )}

                      {err.practice && (() => {
                        const pk = `${group.type}_${i}`
                        const ps = practiceState[pk] || {}
                        const checkPractice = () => {
                          const correct = (err.correct_answer || '').trim().toLowerCase()
                          const given = (ps.answer || '').trim().toLowerCase()
                          const ok = given === correct || correct.includes(given) || given.includes(correct)
                          setPracticeState(prev => ({ ...prev, [pk]: { ...prev[pk], checked: true, correct: ok } }))
                        }
                        return (
                          <div className="mt-2 pt-2 border-t border-gray-700/40">
                            <div className="flex items-center gap-1 mb-1.5">
                              <p className="text-yellow-300 text-xs italic flex-1">Ćwicz: {err.practice}</p>
                              <PlayButton text={err.practice} language={data.language} />
                            </div>
                            {!ps.checked ? (
                              <div className="flex gap-1.5">
                                <input
                                  type="text"
                                  className={`flex-1 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-indigo-500`}
                                  placeholder="Wpisz odpowiedź..."
                                  value={ps.answer || ''}
                                  onChange={e => setPracticeState(prev => ({ ...prev, [pk]: { ...prev[pk], answer: e.target.value } }))}
                                  onKeyDown={e => e.key === 'Enter' && (ps.answer || '').trim() && checkPractice()}
                                />
                                <button
                                  onClick={checkPractice}
                                  disabled={!(ps.answer || '').trim()}
                                  className="px-2 py-1 rounded bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium disabled:opacity-40 transition-colors"
                                >
                                  Sprawdź
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2">
                                <p className={`text-xs font-medium ${ps.correct ? 'text-emerald-400' : 'text-red-400'}`}>
                                  {ps.correct ? 'âś“ Dobrze!' : `âś— Poprawna: ${err.correct_answer}`}
                                </p>
                                <button
                                  onClick={() => setPracticeState(prev => ({ ...prev, [pk]: {} }))}
                                  className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                                >
                                  Spróbuj jeszcze
                                </button>
                              </div>
                            )}
                          </div>
                        )
                      })()}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Voice Chat Analysis */}
      <div className="card mt-6">
        <h2 className="flex items-center gap-2 font-semibold text-lg mb-2">
          <MessageSquare className="w-5 h-5 text-indigo-400" />
          Analiza rozmowy z Voice Chat
        </h2>
        <p className="text-gray-500 text-sm mb-3">Wklej podsumowanie rozmowy z Voice Chat — AI oceni wymowę, gramatykę i płynność.</p>
        <textarea
          className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 resize-none h-28 focus:outline-none focus:border-indigo-500 mb-3"
          placeholder="Wklej tutaj podsumowanie rozmowy z Voice Chat..."
          value={voiceChatText}
          onChange={e => { setvoiceChatText(e.target.value); setvoiceChatAnalysis('') }}
        />
        <button
          onClick={handlevoiceChatAnalysis}
          disabled={voiceChatLoading || !voiceChatText.trim()}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors disabled:opacity-50 mb-3"
        >
          <MessageSquare className="w-4 h-4" />
          {voiceChatLoading ? 'Analizowanie...' : 'Analizuj rozmowę'}
        </button>
        {voiceChatAnalysis && (
          <div className="bg-gray-800/60 rounded-lg p-4 border border-indigo-700/30">
            <pre className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed font-sans">{voiceChatAnalysis}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

