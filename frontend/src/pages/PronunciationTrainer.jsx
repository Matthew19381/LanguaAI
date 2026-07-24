import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mic, MicOff, RotateCcw, ChevronRight, BarChart3, Trophy, CheckCircle } from 'lucide-react'
import { getUserId, addFlashcard, askQuestion, getPronunciationPhrases, analyzePronunciation } from '../api/client'
import { PageLoader } from '../components/LoadingSpinner'
import { useLanguage } from '../hooks/useLanguage'
import PlayButton from '../components/PlayButton'

export default function PronunciationTrainer() {
  const [phrases, setPhrases] = useState([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [recording, setRecording] = useState(false)
  const [result, setResult] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [customPhrase, setCustomPhrase] = useState('')
  const [useCustom, setUseCustom] = useState(false)
  const [sessionResults, setSessionResults] = useState([])
  const [showSummary, setShowSummary] = useState(false)
  const [activityDone, setActivityDone] = useState(false)
  const [flashMsg, setFlashMsg] = useState('')
  const [generatingPhrases, setGeneratingPhrases] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const navigate = useNavigate()
  const userId = getUserId()
  const { t, targetLanguage } = useLanguage()

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
    getPronunciationPhrases(userId)
      .then(r => setPhrases(r?.phrases || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [userId])

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
    markTabComplete('pronunciation')
    setActivityDone(true)
  }

  const currentPhrase = useCustom ? customPhrase : phrases[currentIdx]?.text || ''

  const startRecording = async () => {
    setError('')
    setResult(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach(t => t.stop())
        await analyzeAudio(blob)
      }

      mediaRecorder.start()
      setRecording(true)
    } catch (e) {
      setError(t('pronun.micError'))
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop()
      setRecording(false)
    }
  }

  const analyzeAudio = async (blob) => {
    if (!currentPhrase.trim()) {
      setError(t('pronun.enterPhraseError'))
      return
    }
    setAnalyzing(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('audio', blob, 'recording.webm')
      formData.append('target_text', currentPhrase)
      formData.append('user_id', userId)

      const response = await analyzePronunciation(formData)
      setResult(response.data)
      setSessionResults(prev => [...prev, { phrase: currentPhrase, score: response.data.score, word_scores: response.data.word_scores || [] }])
    } catch (e) {
      const detail = e.response?.data?.detail || e.message
      setError(`${t('pronun.analysisFailed')} ${detail}`)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleAddToFlash = async () => {
    const phrase = useCustom ? customPhrase.trim() : (phrases[currentIdx]?.text || '')
    if (!phrase || !userId) return
    try {
      const res = await addFlashcard(userId, { word: phrase, translation: '' })
      setFlashMsg(res.success === false ? res.message : 'Dodano do fiszek!')
      setTimeout(() => setFlashMsg(''), 3000)
    } catch { setFlashMsg('Błąd.') }
  }

  const handleGeneratePhrases = async () => {
    if (!userId) return
    setGeneratingPhrases(true)
    try {
      const res = await askQuestion(
        `Wygeneruj 5 zdań do ćwiczenia wymowy w języku ${targetLanguage} na poziomie B1. Podaj tylko same zdania, jedno per linia, bez numeracji.`,
        userId
      )
      const lines = (res.answer || '').split('\n').map(l => l.trim()).filter(Boolean).slice(0, 5)
      const newPhrases = lines.map(text => ({ text, source: 'AI' }))
      setPhrases(prev => [...newPhrases, ...prev])
      setCurrentIdx(0)
    } catch {}
    finally { setGeneratingPhrases(false) }
  }

  const nextPhrase = () => {
    setResult(null)
    setCurrentIdx(i => (i + 1) % (phrases.length || 1))
  }

  if (loading) return <PageLoader text={t('pronun.loading')} />

  const scoreColor = result
    ? result.score >= 80 ? 'text-emerald-400'
      : result.score >= 50 ? 'text-yellow-400'
      : 'text-red-400'
    : ''

  return (
    <div className="page-container max-w-xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Mic className="w-7 h-7 text-purple-400" />
        <div>
          <h1 className="text-2xl font-bold">{t('pronun.title')}</h1>
          <p className="text-gray-400">{t('pronun.subtitle')}</p>
        </div>
      </div>

      {!activityDone ? (
        <button
          onClick={handleMarkDone}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700/30 hover:bg-emerald-700/50 border border-emerald-700/40 text-emerald-300 text-sm font-medium transition-colors mb-4"
        >
          <CheckCircle className="w-4 h-4" />
          Oznacz Wymowę jako ukończoną (+10 XP)
        </button>
      ) : (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-900/30 border border-emerald-700/40 text-emerald-400 text-sm font-medium mb-4">
          <CheckCircle className="w-4 h-4" />
          Wymowa ukończona dziś ✓
        </div>
      )}

      {/* Phrase Selection */}
      <div className="card mb-4">
        <div className="flex items-center gap-2 mb-3">
          <button
            onClick={() => setUseCustom(false)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              !useCustom ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {t('pronun.fromLessons')}
          </button>
          <button
            onClick={() => setUseCustom(true)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              useCustom ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {t('pronun.customPhrase')}
          </button>
        </div>

        {useCustom ? (
          <div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                className="input-field flex-1"
                placeholder={t('pronun.enterPhrase')}
                value={customPhrase}
                onChange={e => setCustomPhrase(e.target.value)}
              />
              {customPhrase.trim() && (
                <PlayButton text={customPhrase} language={targetLanguage} />
              )}
            </div>
          </div>
        ) : (
          <div>
            {phrases.length > 0 ? (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-lg font-semibold text-indigo-200">{currentPhrase}</p>
                      <PlayButton text={currentPhrase} language={targetLanguage} />
                    </div>
                    {phrases[currentIdx]?.source && (
                      <p className="text-xs text-gray-500 mt-0.5">{phrases[currentIdx].source}</p>
                    )}
                  </div>
                  <button
                    onClick={nextPhrase}
                    className="p-2 text-gray-400 hover:text-gray-200 transition-colors"
                    title="Next phrase"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={handleAddToFlash}
                    className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    + Dodaj do fiszek
                  </button>
                  {flashMsg && <span className="text-xs text-emerald-400">{flashMsg}</span>}
                </div>
              </>
            ) : (
              <div>
                <p className="text-gray-400 text-sm mb-2">{t('pronun.completeLessons')}</p>
                <button
                  onClick={handleGeneratePhrases}
                  disabled={generatingPhrases}
                  className="text-xs text-indigo-400 hover:text-indigo-300 disabled:opacity-50 transition-colors"
                >
                  {generatingPhrases ? 'Generowanie...' : 'Generuj zdania do ćwiczenia'}
                </button>
              </div>
            )}
            <div className="flex items-center justify-between mt-2">
              {phrases.length > 1 && (
                <p className="text-xs text-gray-600">
                  {currentIdx + 1} / {phrases.length}
                </p>
              )}
              {phrases.length > 0 && (
                <button
                  onClick={handleGeneratePhrases}
                  disabled={generatingPhrases}
                  className="text-xs text-gray-600 hover:text-gray-400 disabled:opacity-50 transition-colors"
                >
                  {generatingPhrases ? '...' : '↻ Generuj nowe'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Recording Control */}
      <div className="card mb-4 text-center">
        <p className="text-gray-400 text-sm mb-4">
          {recording ? t('pronun.recording') : t('pronun.clickMic')}
        </p>
        <button
          onClick={recording ? stopRecording : startRecording}
          disabled={analyzing || (!currentPhrase.trim())}
          className={`w-24 h-24 rounded-full mx-auto flex items-center justify-center transition-all ${
            recording
              ? 'bg-red-600 hover:bg-red-700 animate-pulse'
              : 'bg-purple-700 hover:bg-purple-600'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {recording
            ? <MicOff className="w-10 h-10 text-white" />
            : <Mic className="w-10 h-10 text-white" />
          }
        </button>
        {analyzing && (
          <p className="text-indigo-400 text-sm mt-4 animate-pulse">{t('pronun.analyzing')}</p>
        )}
        {error && (
          <p className="text-red-400 text-sm mt-4">{error}</p>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-lg">{t('pronun.results')}</h2>
            <button
              onClick={() => setResult(null)}
              className="text-gray-500 hover:text-gray-300"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* Score */}
          <div className="text-center mb-4">
            <div className={`text-6xl font-bold ${scoreColor}`}>{result.score}</div>
            <div className="text-gray-400 text-sm">/100</div>
            <div className="progress-bar mt-3">
              <div
                className={`progress-fill ${
                  result.score >= 80 ? 'bg-emerald-500' :
                  result.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${result.score}%` }}
              />
            </div>
          </div>

          {/* Feedback */}
          <div className="bg-gray-800 rounded-lg p-3 mb-4">
            <p className="text-gray-200">{result.feedback}</p>
          </div>

          {/* Transcription */}
          <div className="grid grid-cols-1 gap-3 text-sm">
            <div>
              <span className="text-gray-500">{t('pronun.youSaid')}</span>
              <p className="text-yellow-300 mt-0.5">{result.transcribed || t('pronun.noDetected')}</p>
            </div>
            <div>
              <span className="text-gray-500">{t('pronun.target')}</span>
              <div className="flex items-center gap-2 mt-0.5">
                <p className="text-indigo-200">{result.target}</p>
                <PlayButton text={result.target} language={targetLanguage} />
              </div>
            </div>
          </div>

          {/* Word-by-word */}
          {result.word_scores?.length > 0 && (
            <div className="mt-4">
              <p className="text-gray-500 text-sm mb-2">{t('pronun.wordAnalysis')}</p>
              <div className="flex flex-wrap gap-2">
                {result.word_scores.map((w, i) => (
                  <span
                    key={i}
                    className={`px-2 py-1 rounded text-sm font-medium ${
                      w.correct ? 'bg-emerald-900/40 text-emerald-300' : 'bg-red-900/40 text-red-300'
                    }`}
                  >
                    {w.word}
                    {!w.correct && w.said && (
                      <span className="text-xs text-gray-500 ml-1">({w.said})</span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="flex gap-4 mt-4 text-xs text-gray-500">
            {result.char_similarity !== undefined && (
              <span>{t('pronun.charSimilarity')} <span className="text-gray-300">{result.char_similarity}%</span></span>
            )}
            {result.word_accuracy !== undefined && (
              <span>{t('pronun.wordAccuracy')} <span className="text-gray-300">{result.word_accuracy}%</span></span>
            )}
          </div>

          {/* Next phrase button */}
          <div className="flex gap-2 mt-4">
            <button className="btn-primary flex-1" onClick={() => { setResult(null); if (!useCustom) nextPhrase() }}>
              {t('pronun.nextPhrase')}
            </button>
            {sessionResults.length >= 2 && (
              <button className="btn-secondary flex items-center gap-1" onClick={() => setShowSummary(true)}>
                <BarChart3 className="w-4 h-4" />
                {t('pronun.summary')}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Session Summary */}
      {showSummary && sessionResults.length > 0 && (
        <div className="card mt-4 border-indigo-700/30">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-lg flex items-center gap-2">
              <Trophy className="w-5 h-5 text-yellow-400" />
              {t('pronun.sessionSummary')}
            </h2>
            <button onClick={() => setShowSummary(false)} className="text-gray-500 hover:text-gray-300 text-lg">×</button>
          </div>
          <div className="grid grid-cols-3 gap-3 mb-4 text-center">
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-2xl font-bold text-indigo-400">{sessionResults.length}</div>
              <div className="text-xs text-gray-500 mt-1">{t('pronun.phrasesPracticed')}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <div className={`text-2xl font-bold ${
                Math.round(sessionResults.reduce((s, r) => s + r.score, 0) / sessionResults.length) >= 80
                  ? 'text-emerald-400' : 'text-yellow-400'
              }`}>
                {Math.round(sessionResults.reduce((s, r) => s + r.score, 0) / sessionResults.length)}
              </div>
              <div className="text-xs text-gray-500 mt-1">{t('pronun.avgScore')}</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-2xl font-bold text-emerald-400">
                {Math.max(...sessionResults.map(r => r.score))}
              </div>
              <div className="text-xs text-gray-500 mt-1">{t('pronun.bestScore')}</div>
            </div>
          </div>
          <div className="space-y-2">
            {sessionResults.map((r, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-1 border-b border-gray-800 last:border-0">
                <span className="text-gray-300 truncate flex-1 mr-3">{r.phrase}</span>
                <span className={`font-bold shrink-0 ${r.score >= 80 ? 'text-emerald-400' : r.score >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {r.score}/100
                </span>
              </div>
            ))}
          </div>
          {/* Problem words across session */}
          {(() => {
            const badWords = sessionResults.flatMap(r => r.word_scores.filter(w => !w.correct).map(w => w.word))
            const unique = [...new Set(badWords)]
            if (unique.length === 0) return null
            return (
              <div className="mt-4">
                <p className="text-xs text-gray-500 mb-2">{t('pronun.problemWords')}</p>
                <div className="flex flex-wrap gap-1">
                  {unique.map((w, i) => <span key={i} className="px-2 py-0.5 bg-red-900/30 text-red-300 text-xs rounded">{w}</span>)}
                </div>
              </div>
            )
          })()}
          <button className="btn-secondary w-full mt-4" onClick={() => { setSessionResults([]); setShowSummary(false) }}>
            {t('pronun.resetSession')}
          </button>
        </div>
      )}
    </div>
  )
}
