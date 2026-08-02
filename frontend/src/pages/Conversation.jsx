import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessageSquare, Send, Square, User, Bot,
  Lightbulb, ChevronDown, ChevronUp, BarChart3,
  HelpCircle, AlertCircle, Mic, MicOff
} from 'lucide-react'
import LoadingSpinner from '../components/LoadingSpinner'
import PlayButton from '../components/PlayButton'
import { getUserId, startConversation, sendMessage, analyzeConversation, askQuestion, getVoiceChatPrompt, analyzePastedConversation, sendVoiceMessage, sendVoiceText } from '../api/client'
import { useLanguage } from '../hooks/useLanguage'

const TOPICS = [
  { value: 'everyday conversation', labelKey: 'conv.topic.everyday' },
  { value: 'at a restaurant', labelKey: 'conv.topic.restaurant' },
  { value: 'shopping', labelKey: 'conv.topic.shopping' },
  { value: 'asking for directions', labelKey: 'conv.topic.directions' },
  { value: 'at the doctor', labelKey: 'conv.topic.doctor' },
  { value: 'job interview', labelKey: 'conv.topic.jobInterview' },
  { value: 'talking about hobbies', labelKey: 'conv.topic.hobbies' },
  { value: 'planning a trip', labelKey: 'conv.topic.trip' },
  { value: 'at the hotel', labelKey: 'conv.topic.hotel' },
  { value: 'making friends', labelKey: 'conv.topic.friends' },
]

const MODES = { SETUP: 'setup', CHAT: 'chat', RESULTS: 'results', QA: 'qa' }

// Speech recognition setup
const getSpeechRecognition = () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) return null
  const recognition = new SpeechRecognition()
  recognition.continuous = false
  recognition.interimResults = false
  return recognition
}

// Map targetLanguage to BCP-47 locale
const LANGUAGE_LOCALES = {
  German: 'de-DE',
  English: 'en-US',
  Spanish: 'es-ES',
  Russian: 'ru-RU',
  Chinese: 'zh-CN',
  Polish: 'pl-PL',
  French: 'fr-FR',
}

export default function Conversation() {
  const [mode, setMode] = useState(MODES.SETUP)
  const [topic, setTopic] = useState('everyday conversation')
  const [sessionId, setSessionId] = useState(null)
  const [scenario, setScenario] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [aiTyping, setAiTyping] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [showPhrases, setShowPhrases] = useState(false)
  const [question, setQuestion] = useState('')
  const [qaAnswer, setQaAnswer] = useState('')
  const [qaLoading, setQaLoading] = useState(false)
  const [voiceChatLoading, setVoiceChatLoading] = useState(false)
  const [voiceChatCopied, setVoiceChatCopied] = useState(false)
  const [voiceChatPrompt, setVoiceChatPrompt] = useState('')
  const [showVoiceChatEdit, setShowVoiceChatEdit] = useState(false)
  const [voiceMode, setVoiceMode] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const [pasteLoading, setPasteLoading] = useState(false)
  const [pasteResult, setPasteResult] = useState(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recognitionError, setRecognitionError] = useState('')
  const messagesEndRef = useRef(null)
  const recognitionRef = useRef(null)
  const navigate = useNavigate()
  const userId = getUserId()
  const { t, targetLanguage } = useLanguage()

  useEffect(() => {
    if (!userId) { navigate('/placement'); return }
  }, [userId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleStart = async () => {
    setLoading(true)
    try {
      const res = await startConversation(userId, topic)
      setSessionId(res.session_id)
      setScenario(res)
      setMessages([{ role: 'assistant', content: res.opening_line, id: Date.now() }])
      setMode(MODES.CHAT)
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async (textOverride) => {
    const text = (textOverride || inputText).trim()
    if (!text || !sessionId) return
    const userMsg = { role: "user", content: text, id: Date.now() }
    setMessages(prev => [...prev, userMsg])
    if (!textOverride) setInputText("")
    setAiTyping(true)
    try {
      const res = await sendMessage(sessionId, text)
      setMessages(prev => [...prev, { role: "assistant", content: res.response, id: Date.now() }])
    } catch (e) {
      setMessages(prev => [...prev, { role: "system", content: t("conv.errorResponse"), id: Date.now() }])
    } finally {
      setAiTyping(false)
    }
  }
  const handleVoiceSend = async (textOverride) => {
    const text = (textOverride || inputText).trim()
    if (!text || !userId) return
    const userMsg = { role: "user", content: text, id: Date.now() }
    setMessages(prev => [...prev, userMsg])
    if (!textOverride) setInputText("")
    setAiTyping(true)
    try {
      const res = await sendVoiceMessage(userId, text, targetLanguage)
      setMessages(prev => [...prev, { role: "assistant", content: res.text, id: Date.now() }])
      if (res.audio_base64) {
        try {
          const audioBlob = await fetch(`data:audio/mp3;base64,${res.audio_base64}`).then(r => r.blob())
          const audio = new Audio(URL.createObjectURL(audioBlob))
          audio.play()
        } catch (e) {
          console.error("Audio auto-play failed:", e)
        }
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: "system", content: t("conv.errorResponse"), id: Date.now() }])
    } finally {
      setAiTyping(false)
    }
  }


  const handleEnd = async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const res = await analyzeConversation(sessionId, userId)
      setAnalysis(res)
      setMode(MODES.RESULTS)
    } catch (e) {
      alert('Error analyzing: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAskQuestion = async () => {
    if (!question.trim()) return
    setQaLoading(true)
    try {
      const res = await askQuestion(question, userId)
      setQaAnswer(res.answer)
    } catch (e) {
      setQaAnswer('Error: ' + e.message)
    } finally {
      setQaLoading(false)
    }
  }

  const handleGetVoiceChatPrompt = async () => {
    setVoiceChatLoading(true)
    setVoiceChatCopied(false)
    setShowVoiceChatEdit(false)
    try {
      const res = await getVoiceChatPrompt(userId)
      setVoiceChatPrompt(res.prompt)
      setShowVoiceChatEdit(true)
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setVoiceChatLoading(false)
    }
  }

  const handleCopyVoiceChatPrompt = async () => {
    try {
      await navigator.clipboard.writeText(voiceChatPrompt)
      setVoiceChatCopied(true)
      setTimeout(() => setVoiceChatCopied(false), 3000)
    } catch (e) {
      alert('Copy failed: ' + e.message)
    }
  }

  const toggleRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setRecognitionError('Speech recognition not supported in this browser')
      return
    }

    if (isRecording) {
      // Stop current recognition (user cancel)
      recognitionRef.current?.stop()
      setIsRecording(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    const locale = LANGUAGE_LOCALES[targetLanguage] || 'en-US'
    recognition.lang = locale

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      if (voiceMode) {
        setIsRecording(false)
        setRecognitionError("")
        handleVoiceSend(transcript)
      } else {
        setInputText(prev => prev + transcript)
        setIsRecording(false)
        setRecognitionError("")
      }
    }

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
      setRecognitionError('Błąd rozpoznawania mowy: ' + event.error)
      setIsRecording(false)
    }

    recognition.onend = () => {
      setIsRecording(false)
    }

    try {
      recognition.start()
      recognitionRef.current = recognition
      setIsRecording(true)
      setRecognitionError('')
    } catch (e) {
      setRecognitionError('Failed to start recognition: ' + e.message)
      setIsRecording(false)
    }
  }

  const handleAnalyzePaste = async () => {
    if (!pasteText.trim() || !userId) return
    setPasteLoading(true)
    setPasteResult(null)
    try {
      const res = await analyzePastedConversation(userId, pasteText)
      setPasteResult(res)
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setPasteLoading(false)
    }
  }

  if (mode === MODES.SETUP) {
    return (
      <div className="page-container">
        <div className="flex items-center gap-3 mb-8">
          <MessageSquare className="w-7 h-7 text-emerald-400" />
          <h1 className="text-2xl font-bold">{t('conv.title')}</h1>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Start conversation */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">{t('conv.startTitle')}</h2>
            <p className="text-gray-400 text-sm mb-4">{t('conv.startDesc')}</p>
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">{t('conv.chooseTopic')}</label>
              <select
                className="input-field"
                value={topic}
                onChange={e => setTopic(e.target.value)}
              >
                {TOPICS.map(tp => (
                  <option key={tp.value} value={tp.value}>{t(tp.labelKey)}</option>
                ))}
              </select>
            </div>
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">{t('conv.customTopic')}</label>
              <input
                className="input-field"
                placeholder={t('conv.customPlaceholder')}
                value={topic}
                onChange={e => setTopic(e.target.value)}
              />
            </div>
            <button
              className="btn-success w-full py-3 flex items-center justify-center gap-2"
              onClick={handleStart}
              disabled={loading}
            >
              {loading ? <LoadingSpinner size="sm" /> : <MessageSquare className="w-4 h-4" />}
              {loading ? t('conv.settingUp') : t('conv.start')}
            </button>
          </div>

          {/* Voice Chat Prompt */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-purple-400" />
              {t('conv.voiceChatTitle')}
            </h2>
            <p className="text-gray-400 text-sm mb-4">{t('conv.voiceChatDesc')}</p>
            <button
              className="btn-primary w-full flex items-center justify-center gap-2"
              onClick={handleGetVoiceChatPrompt}
              disabled={voiceChatLoading}
            >
              {voiceChatLoading ? t('conv.voiceChatGenerating') : t('conv.voiceChatButton')}
            </button>
            {showVoiceChatEdit && (
              <div className="mt-3">
                <textarea
                  className="input-field w-full h-40 resize-none text-sm font-mono"
                  value={voiceChatPrompt}
                  onChange={e => setVoiceChatPrompt(e.target.value)}
                />
                <button
                  className="btn-secondary w-full mt-2 flex items-center justify-center gap-2"
                  onClick={handleCopyVoiceChatPrompt}
                >
                  {voiceChatCopied ? t('conv.voiceChatCopied') : t('conv.voiceChatCopyBtn') || 'Kopiuj'}
                </button>
                {voiceChatCopied && (
                  <p className="text-emerald-400 text-sm mt-2 text-center">{t('conv.voiceChatSuccess')}</p>
                )}
              </div>
            )}
          </div>

          {/* Ask a question - full width */}
          <div className="card md:col-span-2">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-blue-400" />
              {t('conv.qaTitle')}
            </h2>
            <p className="text-gray-400 text-sm mb-4">{t('conv.qaDesc')}</p>
            <textarea
              className="input-field h-40 resize-none mb-3"
              placeholder={t('conv.qaPlaceholder')}
              value={question}
              onChange={e => setQuestion(e.target.value)}
            />
            <button
              className="btn-primary w-full mb-3"
              onClick={handleAskQuestion}
              disabled={qaLoading || !question.trim()}
            >
              {qaLoading ? t('conv.qaThinking') : t('conv.qaAsk')}
            </button>
            {qaAnswer && (
              <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-300 leading-relaxed max-h-64 overflow-y-auto whitespace-pre-line">
                {qaAnswer}
              </div>
            )}
          </div>

          {/* Pasted Conversation Analysis */}
          <div className="card md:col-span-2">
            <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-orange-400" />
              Analiza wklejonej rozmowy
            </h2>
            <p className="text-gray-400 text-sm mb-3">
              Wklej podsumowanie lub transkrypt rozmowy z Voice Chat — przeanalizuję Twoje błędy i dodam je do statystyk.
            </p>
            <textarea
              className="input-field h-36 resize-none mb-3 text-sm"
              placeholder="Wklej tutaj transkrypt lub podsumowanie rozmowy..."
              value={pasteText}
              onChange={e => setPasteText(e.target.value)}
            />
            <button
              className="btn-primary w-full mb-3 flex items-center justify-center gap-2"
              onClick={handleAnalyzePaste}
              disabled={pasteLoading || !pasteText.trim()}
            >
              {pasteLoading ? <LoadingSpinner size="sm" /> : <BarChart3 className="w-4 h-4" />}
              {pasteLoading ? 'Analizowanie...' : 'Analizuj błędy'}
            </button>
            {pasteResult && (
              <div className="space-y-3">
                <div className="bg-gray-800 rounded-lg p-4">
                  <p className="text-gray-300 text-sm leading-relaxed">{pasteResult.summary}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className={`text-2xl font-bold ${pasteResult.score >= 70 ? 'text-emerald-400' : pasteResult.score >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {pasteResult.score}%
                    </span>
                    {pasteResult.xp_earned > 0 && (
                      <span className="text-yellow-300 text-sm">+{pasteResult.xp_earned} XP</span>
                    )}
                  </div>
                </div>
                {pasteResult.errors?.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-gray-400 mb-2">Znalezione błędy ({pasteResult.errors.length}):</p>
                    <div className="space-y-2">
                      {pasteResult.errors.slice(0, 8).map((err, i) => {
                        const isCritical = err.severity !== 'minor'
                        return (
                          <div key={i} className={`rounded-lg px-3 py-2 text-sm border-l-2 bg-gray-800 ${isCritical ? 'border-red-600' : 'border-yellow-600'}`}>
                            <div className="flex flex-wrap items-center gap-2 mb-1">
                              <span className={`text-xs px-2 py-0.5 rounded ${isCritical ? 'bg-red-900/40 text-red-300' : 'bg-yellow-900/40 text-yellow-300'}`}>
                                {err.type}
                              </span>
                              <span className={`${isCritical ? 'text-red-400' : 'text-yellow-400'} line-through`}>{err.question}</span>
                              <span className="text-gray-500">â†’</span>
                              <span className="text-emerald-400">{err.correct_answer}</span>
                            </div>
                            {err.explanation && <p className="text-gray-500 text-xs">{err.explanation}</p>}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
                {pasteResult.recommendations?.length > 0 && (
                  <div className="bg-indigo-900/20 border border-indigo-700/30 rounded-lg p-3">
                    <p className="text-xs font-semibold text-indigo-400 mb-1">Rekomendacje:</p>
                    {pasteResult.recommendations.map((r, i) => (
                      <p key={i} className="text-gray-300 text-sm">â€˘ {r}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (mode === MODES.CHAT) {
    return (
      <div className="max-w-2xl mx-auto flex flex-col h-[calc(100vh-64px)]">
        <div className="bg-gray-900 border-b border-gray-800 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold">{scenario?.scenario}</h2>
              <p className="text-gray-400 text-sm">
                {t('conv.you')}: {scenario?.user_role} | {t('conv.ai')}: {scenario?.ai_role}
              </p>
            </div>
            <button
              className="btn-danger text-sm flex items-center gap-1.5"
              onClick={handleEnd}
              disabled={loading}
            >
              {loading ? <LoadingSpinner size="sm" /> : <Square className="w-3 h-3" />}
              {t('conv.endAnalyze')}
            </button>
              <button
                className={`text-sm px-3 py-1.5 rounded-full flex items-center gap-1.5 transition-colors ${
                  voiceMode
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                }`}
                onClick={() => setVoiceMode(!voiceMode)}
                title="Voice Mode: AI responds with audio"
              >
                {voiceMode ? '🔊 Voice ON' : '🔇 Voice OFF'}
              </button>
          </div>

          {scenario?.suggested_phrases?.length > 0 && (
            <div className="mt-3">
              <button
                className="text-indigo-400 text-xs flex items-center gap-1"
                onClick={() => setShowPhrases(!showPhrases)}
              >
                <Lightbulb className="w-3 h-3" />
                {t('conv.usefulPhrases')}
                {showPhrases ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
              {showPhrases && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {scenario.suggested_phrases.map((phrase, i) => (
                    <button
                      key={i}
                      className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-2 py-1 rounded-full transition-colors"
                      onClick={() => setInputText(phrase)}
                    >
                      {phrase}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'assistant' ? 'bg-emerald-700' : 'bg-indigo-700'
              }`}>
                {msg.role === 'assistant' ? <Bot className="w-4 h-4 text-white" /> : <User className="w-4 h-4 text-white" />}
              </div>
              <div className={`max-w-xs lg:max-w-sm rounded-2xl px-4 py-3 relative ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-sm'
                  : msg.role === 'system'
                  ? 'bg-red-900/50 text-red-300 rounded-tl-sm'
                  : 'bg-gray-800 text-gray-100 rounded-tl-sm'
              }`}>
                <p className="text-sm leading-relaxed">{msg.content}</p>
                {msg.role === 'assistant' && (
                  <div className="absolute -top-2 -right-2">
                    <PlayButton text={msg.content} language={targetLanguage} className="w-6 h-6 bg-gray-800 border border-gray-700" />
                  </div>
                )}
              </div>
            </div>
          ))}

          {aiTyping && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-emerald-700 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="bg-gray-900 border-t border-gray-800 p-4">
          <div className="flex gap-3">
            <input
              className="input-field flex-1"
              placeholder={t('conv.typeMessage')}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              disabled={aiTyping}
            />
            <button
              className={`px-3 flex items-center justify-center ${
                isRecording
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
              }`}
              onClick={toggleRecording}
              disabled={aiTyping}
              title={isRecording ? 'Zatrzymaj nagrywanie' : 'Rozpocznij nagrywanie'}
            >
              {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
            <button
              className="btn-primary px-4 flex items-center justify-center"
              onClick={() => handleSend()}
              disabled={!inputText.trim() || aiTyping}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          {recognitionError && (
            <p className="text-red-400 text-xs mt-1 text-center">{recognitionError}</p>
          )}
          <ConvSpecialChars language={targetLanguage} onInsert={ch => setInputText(t => t + ch)} />
          <p className="text-gray-600 text-xs mt-2 text-center">
            {messages.filter(m => m.role === 'user').length} {t('conv.messagesSent')}
          </p>
        </div>
      </div>
    )
  }

  if (mode === MODES.RESULTS && analysis) {
    const score = analysis.score || 0
    return (
      <div className="page-container">
        <div className="flex items-center gap-3 mb-6">
          <BarChart3 className="w-7 h-7 text-emerald-400" />
          <h1 className="text-2xl font-bold">{t('conv.analysisTitle')}</h1>
        </div>

        <div className="card text-center mb-6">
          <div className={`text-5xl font-bold mb-2 ${
            score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {Math.round(score)}%
          </div>
          <p className="text-gray-400">{analysis.summary}</p>
          {analysis.xp_earned > 0 && (
            <span className="badge-blue mt-2 inline-block">+{analysis.xp_earned} XP</span>
          )}
        </div>

        {analysis.strengths?.length > 0 && (
          <div className="card mb-4">
            <h3 className="font-semibold text-emerald-400 mb-3">{t('conv.whatWell')}</h3>
            <ul className="space-y-1">
              {analysis.strengths.map((s, i) => (
                <li key={i} className="text-gray-300 text-sm flex gap-2">
                  <span className="text-emerald-500">âś“</span> {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {analysis.errors?.length > 0 && (
          <div className="card mb-4">
            <h3 className="font-semibold text-red-400 mb-3">{t('conv.errorsReview')}</h3>
            <div className="space-y-3">
              {analysis.errors.map((err, i) => {
                const isCritical = err.severity !== 'minor'
                return (
                  <div key={i} className={`border-l-2 pl-3 ${isCritical ? 'border-red-600' : 'border-yellow-600'}`}>
                    <div className="flex flex-wrap items-center gap-2 text-sm mb-1">
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${isCritical ? 'bg-red-900/40 text-red-300' : 'bg-yellow-900/40 text-yellow-300'}`}>
                        {isCritical ? 'krytyczny' : 'drobny'}
                      </span>
                      {err.type && <span className="text-xs text-gray-500">{err.type}</span>}
                      <span className={`${isCritical ? 'text-red-400' : 'text-yellow-400'} line-through`}>{err.question || err.original}</span>
                      <span className="text-gray-500">â†’</span>
                      <span className="text-emerald-400">{err.correct_answer || err.correction}</span>
                    </div>
                    {err.explanation && <p className="text-gray-500 text-xs">{err.explanation}</p>}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {analysis.recommendations?.length > 0 && (
          <div className="card mb-6">
            <h3 className="font-semibold text-indigo-400 mb-3">{t('conv.recommendations')}</h3>
            <ul className="space-y-2">
              {analysis.recommendations.map((r, i) => (
                <li key={i} className="text-gray-300 text-sm flex gap-2">
                  <span className="text-indigo-400 shrink-0">â€˘</span> {r}
                </li>
              ))}
            </ul>
          </div>
        )}

        <button
          className="btn-primary w-full"
          onClick={() => { setMode(MODES.SETUP); setMessages([]); setAnalysis(null) }}
        >
          {t('conv.newConversation')}
        </button>
      </div>
    )
  }

  return null
}

const CONV_SPECIAL_CHARS = {
  German: ['Ă¤', 'Ă¶', 'ĂĽ', 'Ăź', 'Ă„', 'Ă–', 'Ăś'],
  Spanish: ['á', 'é', 'í', 'ó', 'ú', 'ñ', '¿', '¡'],
  French: ['Ă ', 'Ă˘', 'Ă©', 'Ă¨', 'ĂŞ', 'Ă®', 'Ă´', 'Ăą', 'Ă»', 'Ă§'],
  Portuguese: ['ã', 'â', 'á', 'à', 'ê', 'é', 'í', 'ó', 'ô', 'ú', 'ç'],
  Italian: ['à', 'è', 'é', 'ì', 'ò', 'ó', 'ù'],
}

function ConvSpecialChars({ language, onInsert }) {
  const chars = CONV_SPECIAL_CHARS[language]
  if (!chars) return null
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {chars.map(ch => (
        <button
          key={ch}
          type="button"
          onClick={() => onInsert(ch)}
          className="px-2 py-0.5 rounded bg-gray-700 hover:bg-indigo-700 text-gray-200 text-sm font-mono transition-colors"
        >
          {ch}
        </button>
      ))}
    </div>
  )
}

