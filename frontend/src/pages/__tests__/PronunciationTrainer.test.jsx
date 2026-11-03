import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import PronunciationTrainer from "../PronunciationTrainer"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  addFlashcard: vi.fn(() => Promise.resolve({ success: true })),
  addFlashcardAI: vi.fn(() => Promise.resolve({ success: true })),
  generatePronunciationPhrases: vi.fn(),
  getPronunciationPhrases: vi.fn(),
  analyzePronunciation: vi.fn(),
}))
vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({ t: (key) => key, targetLanguage: "German" }),
}))
vi.mock("../../components/PlayButton", () => ({ default: () => null }))

const PHRASES = [
  { text: "Ich heiße Anna.", translation: "Nazywam się Anna.", source: "Słówko: heißen" },
  { text: "Ich wohne in Berlin.", translation: "", source: "Słówko: wohnen" },
]

describe("PronunciationTrainer (3.11.2026)", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("generated sentences come from the dedicated endpoint and are shown first", async () => {
    const api = await import("../../api/client")
    api.getPronunciationPhrases.mockResolvedValue({ phrases: PHRASES })
    api.generatePronunciationPhrases.mockResolvedValue({ phrases: [{ text: "Über die Brücke fahren wir.", translation: "Jedziemy przez most.", source: "AI" }] })
    render(<MemoryRouter><PronunciationTrainer /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Ich heiße Anna.")).toBeInTheDocument())
    expect(screen.getByText("Nazywam się Anna.")).toBeInTheDocument()
    fireEvent.click(screen.getByText("↻ Generuj nowe"))
    await waitFor(() => expect(screen.getByText("Über die Brücke fahren wir.")).toBeInTheDocument())
    expect(api.generatePronunciationPhrases).toHaveBeenCalledWith(42, 5)
    expect(screen.getByText("1 / 3")).toBeInTheDocument()
  })

  it("a failed generation is shown instead of silently doing nothing", async () => {
    const api = await import("../../api/client")
    api.getPronunciationPhrases.mockResolvedValue({ phrases: PHRASES })
    api.generatePronunciationPhrases.mockRejectedValue(new Error("Nie udało się wygenerować zdań (AI niedostępne). Spróbuj później."))
    render(<MemoryRouter><PronunciationTrainer /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Ich heiße Anna.")).toBeInTheDocument())
    fireEvent.click(screen.getByText("↻ Generuj nowe"))
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("AI niedostępne"))
  })

  it("a sentence goes to flashcards with its translation (was an empty translation)", async () => {
    const api = await import("../../api/client")
    api.getPronunciationPhrases.mockResolvedValue({ phrases: PHRASES })
    render(<MemoryRouter><PronunciationTrainer /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText("Ich heiße Anna.")).toBeInTheDocument())
    fireEvent.click(screen.getByText("+ Dodaj do fiszek"))
    await waitFor(() => expect(api.addFlashcard).toHaveBeenCalledWith(42, { word: "Ich heiße Anna.", translation: "Nazywam się Anna." }))
  })
})
