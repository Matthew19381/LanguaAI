import { useState } from 'react'
import { ShieldCheck, AlertTriangle } from 'lucide-react'

// A7: what the automatic German check did with this lesson (services/lesson_check.py).
export default function LessonQualityNote({ quality }) {
  const [open, setOpen] = useState(false)
  if (!quality) return null
  const corrections = quality.corrections || []
  const issues = quality.open_issues || []
  const failed = quality.review === 'failed'
  return (
    <div className="card mb-6 text-sm space-y-2" data-testid="lesson-quality">
      <button type="button" className="flex items-center gap-2 text-left w-full" onClick={() => setOpen(o => !o)}>
        {failed || issues.length
          ? <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          : <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />}
        <span className="text-gray-300">
          {failed
            ? 'Automatyczna kontrola niemieckiego nie zadziałała: tej lekcji model nie sprawdził.'
            : `Niemiecki sprawdzony automatycznie: ${corrections.length ? `poprawiono ${corrections.length}` : 'bez poprawek'}${issues.length ? `, ${issues.length} do sprawdzenia` : ''}.`}
        </span>
      </button>
      {open && (
        <div className="space-y-2">
          {corrections.length > 0 && (
            <ul className="list-disc ml-5 text-gray-400">
              {corrections.map((c, i) => (
                <li key={i}><span className="line-through">{c.wrong}</span> → <span className="text-emerald-300">{c.correct}</span>{c.reason ? ` (${c.reason})` : ''}</li>
              ))}
            </ul>
          )}
          {issues.length > 0 && (
            <ul className="list-disc ml-5 text-amber-300">
              {issues.map((x, i) => <li key={i}>{x.text}: {x.issue}</li>)}
            </ul>
          )}
          <p className="text-xs text-gray-500">Kontrolę robi model językowy, nie nauczyciel: zmniejsza liczbę błędów, ale ich nie wyklucza.</p>
        </div>
      )}
    </div>
  )
}
