import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import NavBar from '../NavBar'

// Mock the API client — NavBar calls getStats on mount
vi.mock('../../api/client', () => ({
  getUserId: vi.fn(() => null),
  getStats: vi.fn(() => Promise.resolve(null)),
}))

// Mock useLanguage hook — return English labels so tests can find them
vi.mock('../../hooks/useLanguage', () => ({
  useLanguage: () => ({
    t: (key) => {
      const map = {
        'nav.home': 'Home',
        'nav.lesson': 'Lesson',
        'nav.pronounce': 'Pronounce',
        'nav.speak': 'Speak',
        'nav.flashcards': 'Flashcards',
        'nav.test': 'Test',
        'nav.news': 'News',
        'nav.videos': 'Videos',
        'nav.quickmode': '15 min',
        'nav.stats': 'Stats',
        'nav.getStarted': 'Get Started',
      }
      return map[key] || key
    },
    lang: 'en',
    targetLanguage: 'German',
  }),
}))

function renderNavBar(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <NavBar />
    </MemoryRouter>
  )
}

describe('NavBar', () => {
  it('renders the LinguaAI logo text', () => {
    renderNavBar()
    expect(screen.getByText('LinguaAI')).toBeInTheDocument()
  })

  it('renders all nav items', () => {
    renderNavBar()
    expect(screen.getByText('Lesson')).toBeInTheDocument()
    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('Flashcards')).toBeInTheDocument()
    expect(screen.getByText('Speak')).toBeInTheDocument()
    expect(screen.getByText('15 min')).toBeInTheDocument()
    expect(screen.getByText('News')).toBeInTheDocument()
    expect(screen.getByText('Pronounce')).toBeInTheDocument()
    expect(screen.getByText('Stats')).toBeInTheDocument()
  })

  it('renders "Get Started" button when no user is logged in', () => {
    renderNavBar()
    expect(screen.getByText('Get Started')).toBeInTheDocument()
  })

  it('"Get Started" links to /placement', () => {
    renderNavBar()
    const link = screen.getByText('Get Started').closest('a')
    expect(link).toHaveAttribute('href', '/placement')
  })

  it('nav links have correct href attributes', () => {
    renderNavBar()
    const lessonLink = screen.getByText('Lesson').closest('a')
    expect(lessonLink).toHaveAttribute('href', '/lesson')

    const testLink = screen.getByText('Test').closest('a')
    expect(testLink).toHaveAttribute('href', '/test')
  })

  it('renders inside a sticky nav element', () => {
    const { container } = renderNavBar()
    const nav = container.querySelector('nav')
    expect(nav).toBeTruthy()
    expect(nav.className).toContain('sticky')
  })

  // Regression lock for docs/BACKLOG_UX_2026-08.md P3-1: every function must
  // have a permanently-visible label — not hidden below a breakpoint, not
  // behind a hover/menu. Covers every route in App.jsx's Layout, including
  // the Polish-only labels that bypass the t() map.
  it('every nav destination has a label that is not hidden behind a breakpoint class', () => {
    renderNavBar()
    const allLabels = [
      'Lesson', 'Test', 'Speak', 'Pronounce', 'News', 'Bank wiedzy',
      'Flashcards', '15 min', 'Czytaj', 'Błędy', 'Historia', 'Profil', 'Ustawienia',
    ]
    for (const label of allLabels) {
      const el = screen.getByText(label)
      // The label must not sit inside an element whose class hides it at any
      // breakpoint (the old bug: <span className="hidden md:block">).
      let node = el
      while (node && node.tagName !== 'NAV') {
        expect(node.className || '').not.toMatch(/\bhidden\b/)
        node = node.parentElement
      }
    }
  })

  it('groups nav items under visible category headings', () => {
    renderNavBar()
    for (const heading of ['Nauka', 'Ćwiczenia', 'Media', 'Postępy', 'Konto']) {
      expect(screen.getByText(heading)).toBeInTheDocument()
    }
  })
})

describe('NavBar with logged-in user', () => {
  it('does not render "Get Started" when user exists', async () => {
    const { getUserId } = await import('../../api/client')
    getUserId.mockReturnValue(42)

    renderNavBar()
    // userId is set, so "Get Started" should not appear
    expect(screen.queryByText('Get Started')).toBeNull()
  })
})
