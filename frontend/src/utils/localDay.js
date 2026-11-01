// The learner's calendar day (YYYY-MM-DD) in the device's local time zone.
// toISOString() gives the UTC day, so between midnight and 01:00/02:00 in Poland
// the daily caches ("already done today", today's lesson and test) still belonged
// to yesterday (01.11.2026).
export function localDay(date = new Date()) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
