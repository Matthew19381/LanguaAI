import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 120 seconds for AI generation calls
})

// Request interceptor
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

// ===== User / Placement =====

export const createUser = (data) =>
  api.post('/placement/create-user', data)

export const getUser = (userId) =>
  api.get(`/placement/user/${userId}`)

export const startPlacementTest = (data = {}) =>
  api.post('/placement/start', data)

export const submitPlacementTest = (data) =>
  api.post('/placement/submit', data)

export const updateUserLanguage = (userId, targetLanguage) =>
  api.patch(`/placement/${userId}/language`, { target_language: targetLanguage })

export const getLanguageProfiles = (userId) =>
  api.get(`/placement/${userId}/languages`)

// ===== Lessons =====

export const getTodayLesson = (userId) =>
  api.get(`/lessons/today/${userId}`)

export const getLesson = (lessonId, userId) =>
  api.get(`/lessons/${lessonId}`, { params: { user_id: userId } })

export const completeLesson = (lessonId, userId) =>
  api.post(`/lessons/${lessonId}/complete`, { user_id: userId })

export const evaluateProduction = (lessonId, data) =>
  api.post(`/lessons/${lessonId}/evaluate-production`, { ...data, user_id: data.userId })

export const generateTTS = (text, language) =>
  api.post(`/audio/tts`, { text, language })

export const getLessonAudio = (lessonId, userId) =>
  api.get(`/lessons/audio/${lessonId}`, { params: { user_id: userId } })

export const listLessons = (userId) =>
  api.get(`/lessons/list/${userId}`)

export const getLessonHistory = (userId) =>
  api.get(`/lessons/history/${userId}`)

export const generateNextLesson = (userId) =>
  api.post(`/lessons/next/${userId}`)

export const generateConceptFlashcards = (lessonId, userId) =>
  api.post(`/lessons/${lessonId}/concept-flashcards`, null, { params: { user_id: userId } })

export const getLessonConcepts = (userId) =>
  api.get(`/lessons/latest/${userId}/concepts`)

export const recordExerciseError = (lessonId, data) =>
  api.post(`/lessons/${lessonId}/exercise-error`, data)

// ===== Tests =====

export const getDailyTest = (userId) =>
  api.get(`/tests/daily/${userId}`)

export const submitTest = (data) =>
  api.post('/tests/submit', data)

export const getWeeklyTest = (userId, week) =>
  api.get(`/tests/weekly/${userId}`, { params: { week } })

export const getTestHistory = (userId) =>
  api.get(`/tests/history/${userId}`)

export const getTestResult = (resultId) =>
  api.get(`/tests/result/${resultId}`)

export const getTestFromErrors = (userId) =>
  api.get(`/tests/errors/${userId}`)

// ===== Flashcards =====

export const getFlashcards = (userId, params = {}) =>
  api.get(`/flashcards/${userId}`, { params })

export const getDueFlashcards = (userId) =>
  api.get(`/flashcards/${userId}/due`)

export const bulkImportFlashcards = (userId, file) => {
  const formData = new FormData()
  formData.append("file", file)
  return api.post(`/flashcards/${userId}/bulk-import`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
}

export const reviewFlashcard = (flashcardId, rating, userId) =>
  api.post(`/flashcards/${flashcardId}/review`, { rating, user_id: userId })

export const exportAnki = (userId) =>
  api.post(`/flashcards/${userId}/export-anki`, {}, { responseType: 'blob' })

export const addFlashcard = (userId, data) =>
  api.post(`/flashcards/${userId}/add`, data)

export const addFlashcardAI = (userId, word) =>
  api.post(`/flashcards/${userId}/add-ai`, { word })

export const generateFlashcardsFromTopic = (userId, topicId, count = 10) =>
  api.post(`/flashcards/${userId}/generate-from-topic`, { topic_id: topicId, count })

export const generateFlashcardsFromErrors = (userId, count = 10) =>
  api.post('/flashcards/generate-from-errors', { user_id: userId, count })

export const batchAddFlashcards = (userId, flashcards) =>
  api.post('/flashcards/batch-add', { user_id: userId, flashcards })

// ===== Conversation =====

export const startConversation = (userId, topic) =>
  api.post(`/conversation/start/${userId}`, { topic })

export const sendMessage = (sessionId, userMessage) =>
  api.post('/conversation/message', { session_id: sessionId, user_message: userMessage })

export const analyzeConversation = (sessionId, userId) =>
  api.post('/conversation/analyze', { session_id: sessionId, user_id: userId })

export const analyzePastedConversation = (userId, pastedText) =>
  api.post('/conversation/analyze-text', { user_id: userId, pasted_text: pastedText })

export const getVoiceChatPrompt = (userId) =>
  api.get(`/voice-chat/prompt/${userId}`)

export const sendVoiceMessage = (userId, message, language) =>
  api.post('/voice-chat/conversation/voice', { user_id: userId, message, language })

export const sendVoiceText = (userId, message, language) =>
  api.post('/voice-chat/conversation/text', { user_id: userId, message, language })

export const askQuestion = (question, userId) =>
  api.post('/conversation/question', { question, user_id: userId })

export const translateWord = (text, fromLang, toLang, userId) =>
  api.post('/conversation/translate', { text, from_lang: fromLang, to_lang: toLang, user_id: userId })

// ===== Stats =====

export const getStats = (userId) =>
  api.get(`/stats/${userId}`)

export const addXP = (userId, amount, reason) =>
  api.post(`/stats/${userId}/xp`, { amount, reason })

export const getDailyTips = (userId) =>
  api.get(`/tips/${userId}`)

export const getAllErrors = (userId) =>
  api.get(`/stats/${userId}/errors`)

export const getBestStudyTime = (userId) =>
  api.get(`/stats/${userId}/best-study-time`)

// ===== PDF Export =====

export const exportLessonPDF = (lessonId, userId) =>
  axios.get(`/api/lessons/${lessonId}/export-pdf`, { params: { user_id: userId }, responseType: 'blob' })

// ===== Quick Mode =====

export const getQuickMode = (userId) =>
  api.get(`/quickmode/${userId}`)

export const getDictation = (userId, count = 3) =>
  api.get(`/quickmode/dictation/${userId}`, { params: { count } })

// ===== Exercise bank =====

export const getPracticeSet = (userId, { size = 10, topic, includeNew = false } = {}) =>
  api.get(`/exercises/${userId}/practice`, {
    params: { size, topic, include_new: includeNew },
  })

export const answerExercise = (exerciseId, userId, answer, rating) =>
  api.post(`/exercises/${exerciseId}/answer`, { user_id: userId, answer, rating })

export const getExerciseStats = (userId) =>
  api.get(`/exercises/${userId}/stats`)

export const generateExerciseVariants = (userId, skills, perSkill = 2) =>
  api.post(`/exercises/${userId}/generate-variants`, { skills, per_skill: perSkill })

export const checkDictation = (reference, typed) =>
  api.post(`/quickmode/dictation/check`, { reference, typed })

// ===== News =====

export const getNews = (userId, limit = 5) =>
  api.get(`/news/${userId}`, { params: { limit } })

// ===== Pronunciation =====

export const getPronunciationPhrases = (userId) =>
  api.get(`/pronunciation/phrases/${userId}`)

export const analyzePronunciation = (formData) =>
  axios.post('/api/pronunciation/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })

// ===== YouTube =====

export const searchYouTube = (userId, query = '', includePolish = false) =>
  api.get(`/youtube/search`, { params: { user_id: userId, query, include_polish: includePolish } })

// ===== Achievements =====

export const getAchievements = (userId) =>
  api.get(`/stats/${userId}`).then(d => d.achievements)

// ===== localStorage helpers =====

export const getUserId = () => {
  const id = localStorage.getItem('userId')
  if (!id) return null
  const parsed = parseInt(id, 10)
  return (parsed > 0 && !isNaN(parsed)) ? parsed : null
}

export const setUserId = (id) => {
  localStorage.setItem('userId', String(id))
}

export const clearUser = () => {
  localStorage.removeItem('userId')
  localStorage.removeItem('userName')
  localStorage.removeItem('userLanguage')
}

// ===== CSV Export =====

export const exportProgressCSV = (userId) =>
  axios.get(`/api/stats/${userId}/export-csv`, { responseType: 'blob' })

// ===== Obsidian Export =====

export const exportObsidian = (lessonId, userId, dayOffset = 0, upload = false) =>
  axios.get(`/api/lessons/${lessonId}/export-obsidian`, {
    params: { user_id: userId, day_offset: dayOffset, upload },
    responseType: upload ? 'json' : 'blob',
  })

// ===== Study Plan =====

export const getStudyPlan = (userId) =>
  api.get(`/lessons/study-plan/${userId}`)

// ===== Topics =====

export const getTopics = (userId, params = {}) =>
  api.get(`/topics/${userId}`, { params })

export const getTopicTree = (userId, language) =>
  api.get(`/topics/${userId}/tree`, language ? { params: { language } } : {})

export const getDueTopics = (userId, language, limit = 20) =>
  api.get(`/topics/${userId}/due`, { params: { language, limit } })

export const getTopicStats = (userId, language) =>
  api.get(`/topics/${userId}/stats`, language ? { params: { language } } : {})

export const getTopicDetail = (topicId) =>
  api.get(`/topics/detail/${topicId}`)

export const reviewTopic = (topicId, rating) =>
  api.post(`/topics/${topicId}/review`, { rating })

// ===== Lesson Utilities =====

export const resetTodayLesson = (userId) =>
  api.delete(`/lessons/reset-today/${userId}`)

export const getLessonAudioPackage = (lessonId) =>
  axios.get(`/api/lessons/${lessonId}/audio-package`, { responseType: 'blob' })
