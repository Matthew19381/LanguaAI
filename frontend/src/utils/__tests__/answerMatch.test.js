import { describe, it, expect } from 'vitest'
import { matchesAnswer } from '../answerMatch'

// Same cases as backend/tests/test_exercise_open_answers.py (3.11.2026)
describe('answer matching', () => {
  it('a [..] slot accepts any words but not wrong grammar', () => {
    expect(matchesAnswer('Ich wohne in [Twoje miasto].', 'Ich wohne in Leipzig')).toBe(true)
    expect(matchesAnswer('Ich wohne in [Twoje miasto].', 'Ich wohnen in Leipzig')).toBe(false)
    expect(matchesAnswer('Ich wohne in [Twoje miasto].', 'Ich wohne in')).toBe(false)
    expect(matchesAnswer('Ich bin [liczba] Jahre alt.', 'Ich bin 40 Jahre alt.')).toBe(true)
    expect(matchesAnswer('Ich bin [liczba] Jahre alt.', 'Ich bin Jahre alt')).toBe(false)
    expect(matchesAnswer('Przykład: Ich heiße [imię].', 'ich heisse Anna')).toBe(true)
  })
  it('alternatives, punctuation and diacritics', () => {
    expect(matchesAnswer('der Hund / die Katze', 'die Katze')).toBe(true)
    expect(matchesAnswer('Ich sehe den Hund', 'ich sehe den hund!')).toBe(true)
    expect(matchesAnswer('schön', 'schon')).toBe(false)
    expect(matchesAnswer('', 'x')).toBe(false)
  })
})
