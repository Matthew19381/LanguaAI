import { useState, useRef, useEffect, useCallback } from 'react'
import { HelpCircle, X, Target, Send, Loader2 } from 'lucide-react'
import { askAssistant } from '../api/client'

/**
 * AssistantWidget — in-app AI assistant (docs/ASYSTENT_AI_SPEC.md, D-1/D-4).
 * Pilot scope (2026-09-18, t_5fa240f2): mounted ONLY on Lekcja dnia
 * (/lesson, /lesson/:id) and Fiszki (/flashcards) — see Layout.jsx.
 *
 * Three layered input mechanisms, all optional except the text field:
 *  1. Always-available text question (fallback).
 *  2. Auto-attached window.getSelection() text when the widget opens.
 *  3. "Wskaż element" click-to-pick mode (DevTools-Inspect-style): highlights
 *     the element under the cursor, captures a SMALL safe snippet on click
 *     (tag/text/aria-label/nearest heading/data-testid) — never a screenshot
 *     or full DOM dump.
 *
 * Picking mode must not block the rest of the UI: it only activates while
 * the picking button is toggled on, and a single click exits it again.
 */
export default function AssistantWidget({ userId }) {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [picking, setPicking] = useState(false)
  const [pickedElement, setPickedElement] = useState(null)
  const [selectedText, setSelectedText] = useState('')

  const highlightedElRef = useRef(null)
  const textareaRef = useRef(null)

  // Auto-attach the current text selection when the widget opens (D-1 §2).
  useEffect(() => {
    if (!open) return
    try {
      const sel = window.getSelection ? window.getSelection().toString().trim() : ''
      if (sel) setSelectedText(sel)
    } catch { /* ignore — getSelection can throw in odd embedded contexts */ }
  }, [open])

  const clearHighlight = useCallback(() => {
    if (highlightedElRef.current) {
      highlightedElRef.current.style.outline = ''
      highlightedElRef.current.style.outlineOffset = ''
      highlightedElRef.current = null
    }
  }, [])

  const findNearestHeading = (el) => {
    // Walk up and across preceding siblings looking for the closest h1-h3.
    let node = el
    while (node) {
      let sibling = node
      while (sibling) {
        if (sibling.matches && sibling.matches('h1, h2, h3')) {
          return sibling.innerText?.trim() || null
        }
        // Also check descendants of preceding siblings (common layout: a
        // heading wraps deeper inside a preceding card/section).
        if (sibling.querySelector) {
          const heading = sibling.querySelector('h1, h2, h3')
          if (heading) return heading.innerText?.trim() || null
        }
        sibling = sibling.previousElementSibling
      }
      node = node.parentElement
    }
    return null
  }

  const stopPicking = useCallback(() => {
    setPicking(false)
    clearHighlight()
    document.body.style.cursor = ''
  }, [clearHighlight])

  useEffect(() => {
    if (!picking) return

    const handleMouseMove = (e) => {
      const el = document.elementFromPoint(e.clientX, e.clientY)
      if (!el || el === highlightedElRef.current) return
      clearHighlight()
      // Never highlight the widget itself.
      if (el.closest('[data-assistant-widget]')) return
      el.style.outline = '2px solid #6366f1'
      el.style.outlineOffset = '1px'
      highlightedElRef.current = el
    }

    const handleClick = (e) => {
      const el = e.target
      if (el && !el.closest('[data-assistant-widget]')) {
        e.preventDefault()
        e.stopPropagation()
        setPickedElement({
          tag: el.tagName,
          text: el.innerText?.slice(0, 200) || null,
          aria_label: el.getAttribute('aria-label'),
          nearest_heading: findNearestHeading(el),
          testid: el.getAttribute('data-testid'),
        })
      }
      stopPicking()
    }

    document.body.style.cursor = 'crosshair'
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('click', handleClick, true)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('click', handleClick, true)
    }
  }, [picking, clearHighlight, stopPicking])

  const startPicking = () => setPicking(true)
  const cancelPickedElement = () => setPickedElement(null)
  const clearSelectedText = () => setSelectedText('')

  const handleAsk = async () => {
    if (!question.trim()) return
    setLoading(true)
    setError('')
    setAnswer('')
    try {
      const res = await askAssistant({
        user_id: userId,
        question: question.trim(),
        route: window.location.pathname,
        element_context: pickedElement || null,
        selected_text: selectedText || null,
      })
      if (res.success) {
        setAnswer(res.answer)
      } else {
        setError(res.answer || 'Asystent jest chwilowo niedostępny.')
      }
    } catch {
      setError('Asystent jest chwilowo niedostępny, spróbuj ponownie.')
    } finally {
      setLoading(false)
    }
  }

  const close = () => {
    setOpen(false)
    setQuestion('')
    setAnswer('')
    setError('')
    setPickedElement(null)
    setSelectedText('')
    stopPicking()
  }

  return (
    <div className="fixed bottom-safe-6 right-20 z-40" data-assistant-widget>
      {open ? (
        <div className="dark:bg-gray-900 bg-white dark:border dark:border-gray-700 border border-gray-200 rounded-xl shadow-2xl p-3 w-80">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-semibold dark:text-gray-200 text-gray-800">Asystent</span>
            </div>
            <button onClick={close} aria-label="Zamknij asystenta">
              <X className="w-4 h-4 dark:text-gray-500 text-gray-400 dark:hover:text-gray-300 hover:text-gray-600" />
            </button>
          </div>

          <button
            onClick={startPicking}
            disabled={picking}
            className="w-full mb-2 py-1.5 rounded-lg dark:bg-gray-800 bg-gray-100 dark:hover:bg-gray-700 hover:bg-gray-200 dark:border dark:border-gray-700 border border-gray-300 text-xs text-indigo-500 font-medium flex items-center justify-center gap-1.5 transition-colors disabled:opacity-60"
          >
            <Target className="w-3.5 h-3.5" />
            {picking ? 'Kliknij na element na ekranie...' : 'Wskaż element'}
          </button>

          {pickedElement && (
            <div className="mb-2 p-2 dark:bg-gray-800 bg-indigo-50 rounded-lg text-xs dark:text-gray-300 text-gray-700 flex items-center justify-between gap-2">
              <span>
                Wskazano: {pickedElement.tag}
                {pickedElement.text ? ` — "${pickedElement.text.slice(0, 40)}"` : ''}
              </span>
              <button onClick={cancelPickedElement} aria-label="Anuluj wskazany element" className="shrink-0">
                <X className="w-3 h-3 dark:text-gray-500 text-gray-400" />
              </button>
            </div>
          )}

          {selectedText && (
            <div className="mb-2 p-2 dark:bg-gray-800 bg-indigo-50 rounded-lg text-xs dark:text-gray-300 text-gray-700 flex items-center justify-between gap-2">
              <span>Zaznaczono: "{selectedText.slice(0, 60)}"</span>
              <button onClick={clearSelectedText} aria-label="Wyczyść zaznaczenie" className="shrink-0">
                <X className="w-3 h-3 dark:text-gray-500 text-gray-400" />
              </button>
            </div>
          )}

          <textarea
            ref={textareaRef}
            className="w-full dark:bg-gray-800 bg-gray-50 dark:border dark:border-gray-700 border border-gray-300 rounded-lg p-2 text-sm dark:text-gray-200 text-gray-800 resize-none h-16 focus:outline-none focus:border-indigo-500 dark:placeholder-gray-500 placeholder-gray-400"
            placeholder="Zapytaj o cokolwiek na tym ekranie..."
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAsk() } }}
          />

          <button
            onClick={handleAsk}
            disabled={loading || !question.trim()}
            className="w-full mt-2 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {loading ? 'Pytam...' : 'Zapytaj'}
          </button>

          {answer && (
            <div className="mt-2 p-2.5 dark:bg-gray-800 bg-indigo-50 rounded-lg dark:border dark:border-indigo-700/30 border border-indigo-200">
              <p className="text-sm dark:text-emerald-300 text-emerald-700 leading-relaxed whitespace-pre-wrap">{answer}</p>
            </div>
          )}
          {error && (
            <div className="mt-2 p-2.5 dark:bg-red-900/20 bg-red-50 rounded-lg dark:border dark:border-red-700/30 border border-red-200">
              <p className="text-sm dark:text-red-300 text-red-700">{error}</p>
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 dark:bg-gray-800 bg-white hover:bg-indigo-600 dark:border dark:border-gray-700 border border-gray-200 dark:hover:border-indigo-600 dark:text-gray-300 text-gray-600 hover:text-white px-3 py-2 rounded-xl shadow-lg transition-all"
          title="Asystent"
          aria-label="Asystent"
        >
          <HelpCircle className="w-5 h-5" />
          <span className="text-sm font-medium hidden sm:inline">Asystent</span>
        </button>
      )}
    </div>
  )
}
