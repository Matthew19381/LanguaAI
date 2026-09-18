import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Layout from '../Layout'

vi.mock('../../api/client', () => ({
  getUserId: vi.fn(() => 42),
  getStats: vi.fn(() => Promise.resolve({ new_achievements: [] })),
  askQuestion: vi.fn(() => Promise.resolve({ answer: '' })),
  translateWord: vi.fn(() => Promise.resolve({ translation: '' })),
  addFlashcard: vi.fn(() => Promise.resolve({})),
  askAssistant: vi.fn(() => Promise.resolve({ success: true, answer: 'ok' })),
}))

vi.mock('../../hooks/useLanguage', () => ({
  useLanguage: () => ({ t: (key) => key, targetLanguage: 'German' }),
}))

vi.mock('../../hooks/useDarkMode', () => ({
  useDarkMode: () => ({ dark: false, toggle: vi.fn() }),
}))

vi.mock('../NavBar', () => ({ default: () => <nav>NavBar</nav> }))
vi.mock('../NotificationManager', () => ({ default: () => null }))
vi.mock('../OfflineBanner', () => ({ default: () => null }))

function renderLayout(initialPath) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route path="lesson" element={<div>Lesson page</div>} />
          <Route path="flashcards" element={<div>Flashcards page</div>} />
          <Route path="stats" element={<div>Stats page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe('Layout — AssistantWidget pilot scope (docs/ASYSTENT_AI_SPEC.md)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shows the assistant widget on /lesson', async () => {
    renderLayout('/lesson')
    await waitFor(() => expect(screen.getByText('Lesson page')).toBeInTheDocument())
    expect(screen.getByLabelText('Asystent')).toBeInTheDocument()
  })

  it('shows the assistant widget on /flashcards', async () => {
    renderLayout('/flashcards')
    await waitFor(() => expect(screen.getByText('Flashcards page')).toBeInTheDocument())
    expect(screen.getByLabelText('Asystent')).toBeInTheDocument()
  })

  it('does not show the assistant widget on other pages (e.g. /stats)', async () => {
    renderLayout('/stats')
    await waitFor(() => expect(screen.getByText('Stats page')).toBeInTheDocument())
    expect(screen.queryByLabelText('Asystent')).not.toBeInTheDocument()
  })

  it('the translator widget still renders everywhere, unaffected by the assistant scope', async () => {
    renderLayout('/stats')
    await waitFor(() => expect(screen.getByText('Stats page')).toBeInTheDocument())
    expect(screen.getByLabelText('Tłumacz')).toBeInTheDocument()
  })
})
