import { useState, useEffect } from 'react'

const STORAGE_KEY = 'linguaai_dark_mode'

export function useDarkMode() {
  const [dark, setDark] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored !== null) return stored === 'true'
    } catch {}
    return true // default: dark mode
  })

  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.remove('dark')
      root.classList.add('light')
    }
    localStorage.setItem(STORAGE_KEY, String(dark))
    // Phone status bar matches the header instead of a fixed purple
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', dark ? '#111827' : '#ffffff')
  }, [dark])

  const toggle = () => setDark(d => !d)

  return { dark, toggle }
}
