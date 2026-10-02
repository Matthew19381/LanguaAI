import { describe, it, expect, beforeEach } from 'vitest'
import {
  DEFAULT_FLASHCARD_AUDIO, loadFlashcardAudio, saveFlashcardAudio, autoPlayTexts,
} from '../flashcardAudio'

const card = { word: 'der Hund', example_sentence: 'Der Hund schläft.' }
const ALL_ON = { frontWord: true, frontSentence: true, backWord: true, backSentence: true }

beforeEach(() => {
  localStorage.clear()
})

describe('flashcard audio settings', () => {
  it('falls back to defaults when nothing is stored', () => {
    expect(loadFlashcardAudio()).toEqual(DEFAULT_FLASHCARD_AUDIO)
  })

  it('round-trips through localStorage, filling keys added later', () => {
    saveFlashcardAudio({ backWord: false })
    expect(loadFlashcardAudio()).toEqual({ ...DEFAULT_FLASHCARD_AUDIO, backWord: false })
  })

  it('survives corrupted storage', () => {
    localStorage.setItem('flashcardAudio', '{not json')
    expect(loadFlashcardAudio()).toEqual(DEFAULT_FLASHCARD_AUDIO)
  })
})

describe('autoPlayTexts', () => {
  it('plays word then sentence on the back', () => {
    expect(autoPlayTexts(card, { flipped: true, reversed: false, cloze: false }, ALL_ON))
      .toEqual(['der Hund', 'Der Hund schläft.'])
  })

  it('plays the front in target → PL mode', () => {
    expect(autoPlayTexts(card, { flipped: false, reversed: false, cloze: false }, ALL_ON))
      .toEqual(['der Hund', 'Der Hund schläft.'])
  })

  it('never gives the answer away on the front in PL → target mode', () => {
    expect(autoPlayTexts(card, { flipped: false, reversed: true, cloze: false }, ALL_ON)).toEqual([])
  })

  it('never fills the cloze blank on the front', () => {
    expect(autoPlayTexts(card, { flipped: false, reversed: false, cloze: true }, ALL_ON)).toEqual([])
  })

  it('still plays the back in PL → target mode', () => {
    expect(autoPlayTexts(card, { flipped: true, reversed: true, cloze: false }, ALL_ON))
      .toEqual(['der Hund', 'Der Hund schläft.'])
  })

  it('skips a missing example sentence and a missing card', () => {
    expect(autoPlayTexts({ word: 'ja' }, { flipped: true }, ALL_ON)).toEqual(['ja'])
    expect(autoPlayTexts(undefined, { flipped: true }, ALL_ON)).toEqual([])
  })

  it('defaults to the word only, after reveal', () => {
    expect(autoPlayTexts(card, { flipped: false }, DEFAULT_FLASHCARD_AUDIO)).toEqual([])
    expect(autoPlayTexts(card, { flipped: true }, DEFAULT_FLASHCARD_AUDIO)).toEqual(['der Hund'])
  })
})
