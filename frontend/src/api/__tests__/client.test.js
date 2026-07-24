import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { getUserId, setUserId, clearUser } from '../client'

// ---------------------------------------------------------------------------
// localStorage helpers — these are pure functions with no HTTP calls
// ---------------------------------------------------------------------------

describe('getUserId', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('returns null when nothing is stored', () => {
    expect(getUserId()).toBeNull()
  })

  it('returns a number after setUserId', () => {
    setUserId(42)
    expect(getUserId()).toBe(42)
    expect(typeof getUserId()).toBe('number')
  })

  it('parses string-stored IDs as integers', () => {
    localStorage.setItem('userId', '7')
    expect(getUserId()).toBe(7)
  })
})

describe('setUserId', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('stores the id as a string in localStorage', () => {
    setUserId(99)
    expect(localStorage.getItem('userId')).toBe('99')
  })

  it('can store large IDs', () => {
    setUserId(1000000)
    expect(getUserId()).toBe(1000000)
  })
})

describe('clearUser', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('removes userId', () => {
    setUserId(5)
    clearUser()
    expect(getUserId()).toBeNull()
  })

  it('removes userName', () => {
    localStorage.setItem('userName', 'Anna')
    clearUser()
    expect(localStorage.getItem('userName')).toBeNull()
  })

  it('removes userLanguage', () => {
    localStorage.setItem('userLanguage', 'German')
    clearUser()
    expect(localStorage.getItem('userLanguage')).toBeNull()
  })

  it('is idempotent — safe to call on empty storage', () => {
    expect(() => clearUser()).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// API function exports — verify they exist and are functions
// ---------------------------------------------------------------------------

describe('API function exports', () => {
  it('exports all expected API functions', async () => {
    const client = await import('../client')
    const expectedExports = [
      'createUser', 'getUser', 'startPlacementTest', 'submitPlacementTest',
      'getTodayLesson', 'getLesson', 'completeLesson', 'getLessonAudio',
      'listLessons', 'exportLessonPDF',
      'getDailyTest', 'submitTest', 'getWeeklyTest', 'getTestHistory',
      'getTestResult',
      'getFlashcards', 'getDueFlashcards', 'reviewFlashcard', 'exportAnki',
      'addFlashcard',
      'startConversation', 'sendMessage', 'analyzeConversation', 'askQuestion',
      'getStats', 'getDailyTips',
      'getQuickMode', 'getNews',
      'getPronunciationPhrases', 'analyzePronunciation',
      'getAchievements',
      'getUserId', 'setUserId', 'clearUser',
    ]
    for (const name of expectedExports) {
      expect(typeof client[name], `${name} should be a function`).toBe('function')
    }
  })
})
