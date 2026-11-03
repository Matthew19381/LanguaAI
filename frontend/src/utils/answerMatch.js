// Mirrors grade_answer() in backend/services/exercise_service.py.
// Case, spacing and punctuation do not count, "ss" stands for "ß", diacritics
// count ("schon" ≠ "schön"). "a / b" or "a | b" lists accepted answers (a slash
// without spaces belongs to the answer: "der/die Kollege/-in"), a
// leading "Przykład:" marks a sample, and a "[...]" slot ("Ich wohne in
// [Twoje miasto]") accepts any words (3.11.2026).
// Python's \w is Unicode-aware, JavaScript's is ASCII-only, so explicit
// Unicode classes are used here.
const PUNCT = /[^\p{L}\p{N}_\s]/gu
const SLOT = /\[[^\]]*\]/g
const SAMPLE_PREFIX = /^\s*(przyk[lł]ad|np|example|z\.?\s*b)\s*[.:]\s*/i

export function normalizeAnswer(text) {
  return String(text || '').trim().toLowerCase().replace(/ß/g, 'ss').replace(PUNCT, '').replace(/\s+/g, ' ').trim()
}

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

export function hasSlot(expected) {
  return /\[[^\]]*\]/.test(String(expected || ''))
}

export function matchesAnswer(expected, given) {
  const g = normalizeAnswer(given)
  if (!g) return false
  const alts = String(expected || '').replace(SAMPLE_PREFIX, '').split(/\s+\/\s+|\s*\|\s*/).filter(a => a.trim())
  return alts.some(alt => {
    if (hasSlot(alt)) {
      const fixed = alt.split(SLOT).map(normalizeAnswer)
      return new RegExp('^' + fixed.map(escapeRe).join('\\s*\\S.*?\\s*') + '$', 'u').test(g)
    }
    const a = normalizeAnswer(alt)
    return a.length > 0 && a === g
  })
}
