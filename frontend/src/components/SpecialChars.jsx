// Shared special-character helper for target-language input (ä ö ü ß, etc.).
//
// Two problems this fixes vs. the old inline version:
//  1. Clicking a char button used to steal focus from the input first (the
//     caret "disappeared"). `onMouseDown preventDefault` keeps focus in the
//     field, so the click never blurs it.
//  2. The char is inserted AT THE CARET (selectionStart/End), not appended to
//     the end, and the caret is restored right after it.
//
// Usage:
//   const ref = useRef(null)
//   <textarea ref={ref} value={val} onChange={e => setVal(e.target.value)} />
//   <SpecialChars language={lang} inputRef={ref} value={val} onChange={setVal} />
//
// `onChange` receives the new full string. If no inputRef is given (or the
// element has no selection API), it falls back to appending at the end.

export const SPECIAL_CHARS = {
  German: ['ä', 'ö', 'ü', 'ß', 'Ä', 'Ö', 'Ü'],
  Spanish: ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'ü', '¿', '¡'],
  French: ['à', 'â', 'ç', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ù', 'û', 'œ'],
  Italian: ['à', 'è', 'é', 'ì', 'ò', 'ù'],
  Portuguese: ['á', 'â', 'ã', 'à', 'ç', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú'],
  Russian: null, // Cyrillic — keyboard handles it
  Chinese: null,
}

export default function SpecialChars({ language, inputRef, value = '', onChange, className = '' }) {
  const chars = SPECIAL_CHARS[language]
  if (!chars || !onChange) return null

  const insert = (ch) => {
    const el = inputRef?.current
    if (el && typeof el.selectionStart === 'number') {
      const start = el.selectionStart
      const end = el.selectionEnd
      const next = value.slice(0, start) + ch + value.slice(end)
      onChange(next)
      // Restore caret after React re-renders the controlled value.
      requestAnimationFrame(() => {
        try {
          el.focus()
          const pos = start + ch.length
          el.setSelectionRange(pos, pos)
        } catch { /* element unmounted */ }
      })
    } else {
      onChange((value || '') + ch)
    }
  }

  return (
    <div className={`flex flex-wrap gap-1 mt-1 ${className}`}>
      {chars.map(ch => (
        <button
          key={ch}
          type="button"
          // Prevents the button from stealing focus from the input on click.
          onMouseDown={e => e.preventDefault()}
          onClick={() => insert(ch)}
          className="px-2 py-0.5 rounded dark:bg-gray-700 bg-gray-200 dark:hover:bg-indigo-700 hover:bg-indigo-300 dark:text-gray-200 text-gray-800 text-sm font-mono transition-colors"
        >
          {ch}
        </button>
      ))}
    </div>
  )
}
