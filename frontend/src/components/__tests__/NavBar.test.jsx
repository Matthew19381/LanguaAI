import { render, screen, within, fireEvent } from '@testing-library/react'
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
    const screen = within(document.querySelector('[data-testid="nav-desktop"]'))
    expect(screen.getByText('Lesson')).toBeInTheDocument()
    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('Flashcards')).toBeInTheDocument()
    expect(screen.getByText('Speak')).toBeInTheDocument()
    expect(screen.queryByText('15 min')).not.toBeInTheDocument()   // timer left the menu (3.11)
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
    const screen = within(document.querySelector('[data-testid="nav-desktop"]'))
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

  // Regression lock for docs/BACKLOG_UX_2026-08.md P3-1 (DoD: every function
  // reachable from navigation with a readable label). Since 1.11.2026 phones
  // get a bottom bar + "Wszystko" sheet, md+ keeps the grouped links. Both
  // lists must contain every route in App.jsx's Layout, each with its label.
  const allLabels = [
    'Home', 'Lesson', 'Test', 'Speak', 'Pronounce', 'Egzamin B1', 'News', 'Bank wiedzy',
    'Flashcards', 'nav.practice', 'nav.dictation', 'Na głos', 'Videos',
    'Stats', 'Błędy', 'Historia', 'Profil', 'Ustawienia',
  ]

  it('md+ nav lists every destination with a text label', () => {
    renderNavBar()
    const desktop = within(screen.getByTestId('nav-desktop'))
    for (const label of allLabels) {
      expect(desktop.getByText(label).closest('a')).toBeTruthy()
    }
  })

  it('phone bottom bar has 4 labelled destinations and a "Wszystko" button', () => {
    renderNavBar()
    const bar = within(screen.getByTestId('nav-bottom'))
    expect(bar.getAllByRole('link').map(a => a.textContent)).toEqual(['Home', 'Lesson', 'Flashcards', 'Speak'])
    expect(bar.getByRole('button', { name: /Wszystko/ })).toHaveAttribute('aria-expanded', 'false')
  })

  it('"Wszystko" opens every destination, each with a label not hidden by a breakpoint', () => {
    renderNavBar()
    fireEvent.click(screen.getByTestId('nav-all-button'))
    const dialog = screen.getByRole('dialog', { name: 'Wszystkie funkcje' })
    for (const label of allLabels) {
      const el = within(dialog).getByText(label)
      expect(el.closest('a')).toBeTruthy()
      let node = el
      while (node && node !== dialog) {
        expect(node.className || '').not.toMatch(/(^|\s)hidden\b/)
        node = node.parentElement
      }
    }
    expect(within(dialog).getByText('Lesson').closest('a')).toHaveAttribute('href', '/lesson')
  })

  it('"Wszystko" closes with Escape', () => {
    renderNavBar()
    fireEvent.click(screen.getByTestId('nav-all-button'))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('groups nav items under visible category headings', () => {
    renderNavBar()
    const desktop = within(screen.getByTestId('nav-desktop'))
    for (const heading of ['Nauka', 'Ćwiczenia', 'Media', 'Postępy', 'Konto']) {
      expect(desktop.getByText(heading)).toBeInTheDocument()
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

describe('NavBar translator button (A10)', () => {
  it('opens the translator from the header when Layout passes the handler', async () => {
    const { fireEvent } = await import('@testing-library/react')
    const onOpen = vi.fn()
    render(<MemoryRouter><NavBar onOpenTranslator={onOpen} /></MemoryRouter>)
    fireEvent.click(screen.getByTestId('nav-translator'))
    expect(onOpen).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('nav-translator').className).toContain('sm:hidden')
  })

  it('has no translator button without the handler', () => {
    renderNavBar()
    expect(screen.queryByTestId('nav-translator')).toBeNull()
  })

  it('3.11: news is "Czytaj", reading aloud is "Na głos", no timer entry in the menu', async () => {
    const { default: translations } = await import('../../i18n/translations')
    expect(translations.pl['nav.news']).toBe('Czytaj')
    renderNavBar()
    const desktop = within(screen.getByTestId('nav-desktop'))
    expect(desktop.getByText('Na głos').closest('a')).toHaveAttribute('href', '/read-aloud')
    expect(document.querySelector('[data-testid="nav-desktop"] a[href="/quickmode"]')).toBeNull()
  })
})
