// Flashcard auto-play preferences (Settings → "Audio fiszek").
// Stored per device on purpose: whether sound is welcome depends on where
// you're studying (phone on a bus vs. a desk), so it doesn't sync via backend.
const STORAGE_KEY = 'flashcardAudio'

// Default: hear the word once the card is revealed — links spelling to sound
// right after the recall attempt, without slowing the review down.
export const DEFAULT_FLASHCARD_AUDIO = {
  frontWord: false,
  frontSentence: false,
  backWord: true,
  backSentence: false,
}

export function loadFlashcardAudio() {
  try {
    return { ...DEFAULT_FLASHCARD_AUDIO, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
  } catch {
    return { ...DEFAULT_FLASHCARD_AUDIO }
  }
}

export function saveFlashcardAudio(settings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch { /* storage blocked — setting just won't persist */ }
}

// Texts to auto-play when a card side becomes visible. The front never plays
// anything that gives the answer away: in PL→target mode the target word IS
// the answer, and in cloze mode both the word and the sentence fill the blank.
export function autoPlayTexts(card, { flipped, reversed, cloze }, settings) {
  if (!card) return []
  const texts = []
  if (flipped) {
    if (settings.backWord) texts.push(card.word)
    if (settings.backSentence) texts.push(card.example_sentence)
  } else if (!reversed && !cloze) {
    if (settings.frontWord) texts.push(card.word)
    if (settings.frontSentence) texts.push(card.example_sentence)
  }
  return texts.filter(Boolean)
}
