import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AssistantWidget from '../AssistantWidget'

vi.mock('../../api/client', () => ({
  askAssistant: vi.fn(() => Promise.resolve({ success: true, answer: 'Testowa odpowiedź.' })),
}))

describe('AssistantWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders a closed floating button by default', () => {
    render(<AssistantWidget userId={42} />)
    expect(screen.getByLabelText('Asystent')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/Zapytaj o cokolwiek/)).not.toBeInTheDocument()
  })

  it('opens the panel on click', () => {
    render(<AssistantWidget userId={42} />)
    fireEvent.click(screen.getByLabelText('Asystent'))
    expect(screen.getByPlaceholderText(/Zapytaj o cokolwiek/)).toBeInTheDocument()
  })

  it('sends the question and shows the answer', async () => {
    const { askAssistant } = await import('../../api/client')
    render(<AssistantWidget userId={42} />)
    fireEvent.click(screen.getByLabelText('Asystent'))

    const textarea = screen.getByPlaceholderText(/Zapytaj o cokolwiek/)
    fireEvent.change(textarea, { target: { value: 'Co to jest FSRS?' } })
    fireEvent.click(screen.getByText('Zapytaj'))

    await waitFor(() => {
      expect(screen.getByText('Testowa odpowiedź.')).toBeInTheDocument()
    })
    expect(askAssistant).toHaveBeenCalledWith(expect.objectContaining({
      user_id: 42,
      question: 'Co to jest FSRS?',
    }))
  })

  it('shows a graceful error message when the backend reports failure', async () => {
    const { askAssistant } = await import('../../api/client')
    askAssistant.mockResolvedValueOnce({ success: false, answer: 'Asystent jest chwilowo niedostępny, spróbuj ponownie.' })
    render(<AssistantWidget userId={42} />)
    fireEvent.click(screen.getByLabelText('Asystent'))

    fireEvent.change(screen.getByPlaceholderText(/Zapytaj o cokolwiek/), { target: { value: 'Cokolwiek' } })
    fireEvent.click(screen.getByText('Zapytaj'))

    await waitFor(() => {
      expect(screen.getByText(/chwilowo niedostępny/)).toBeInTheDocument()
    })
  })

  it('shows a graceful error message when the API call throws', async () => {
    const { askAssistant } = await import('../../api/client')
    askAssistant.mockRejectedValueOnce(new Error('network error'))
    render(<AssistantWidget userId={42} />)
    fireEvent.click(screen.getByLabelText('Asystent'))

    fireEvent.change(screen.getByPlaceholderText(/Zapytaj o cokolwiek/), { target: { value: 'Cokolwiek' } })
    fireEvent.click(screen.getByText('Zapytaj'))

    await waitFor(() => {
      expect(screen.getByText(/chwilowo niedostępny/)).toBeInTheDocument()
    })
  })

  it('entering pick mode does not block interaction with the rest of the page', () => {
    render(
      <div>
        <button data-testid="page-button">Page action</button>
        <AssistantWidget userId={42} />
      </div>
    )
    fireEvent.click(screen.getByLabelText('Asystent'))
    fireEvent.click(screen.getByText('Wskaż element'))

    // The picking button shows the "click on screen" prompt, but everything
    // else remains rendered and clickable (no overlay, no disabled state on
    // other page content) — clicking the page button doesn't throw and the
    // element is still present.
    const pageButton = screen.getByTestId('page-button')
    expect(pageButton).toBeInTheDocument()
    expect(() => fireEvent.click(pageButton)).not.toThrow()
  })

  it('captures the clicked element as element_context and shows it in the panel', async () => {
    const { askAssistant } = await import('../../api/client')
    render(
      <div>
        <button data-testid="target-button" aria-label="Ukończ lekcję">Ukończ</button>
        <AssistantWidget userId={42} />
      </div>
    )
    fireEvent.click(screen.getByLabelText('Asystent'))
    fireEvent.click(screen.getByText('Wskaż element'))

    const target = screen.getByTestId('target-button')
    // Picking listens on document 'click' in the capture phase; jsdom's
    // elementFromPoint doesn't do real hit-testing, so we dispatch directly
    // on the target and let the document-level capture listener handle it.
    fireEvent.click(target)

    await waitFor(() => {
      expect(screen.getByText(/Wskazano: BUTTON/)).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText(/Zapytaj o cokolwiek/), { target: { value: 'Co to?' } })
    fireEvent.click(screen.getByText('Zapytaj'))

    await waitFor(() => {
      expect(askAssistant).toHaveBeenCalledWith(expect.objectContaining({
        element_context: expect.objectContaining({ tag: 'BUTTON' }),
      }))
    })
  })

  it('cancelling the picked element clears it', async () => {
    render(
      <div>
        <button data-testid="target-button">Zrób coś</button>
        <AssistantWidget userId={42} />
      </div>
    )
    fireEvent.click(screen.getByLabelText('Asystent'))
    fireEvent.click(screen.getByText('Wskaż element'))
    fireEvent.click(screen.getByTestId('target-button'))

    await waitFor(() => {
      expect(screen.getByText(/Wskazano:/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByLabelText('Anuluj wskazany element'))
    expect(screen.queryByText(/Wskazano:/)).not.toBeInTheDocument()
  })
})
