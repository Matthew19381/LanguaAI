import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import News from "../News"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  addFlashcard: vi.fn(() => Promise.resolve({ success: true })),
  addFlashcardAI: vi.fn(() => Promise.resolve({ success: true })),
  translateWord: vi.fn(),
  getNews: vi.fn(() => Promise.resolve({ articles: [{
    title: "Neues Museum", simplified_text: "Das Museum ist neu. Viele Leute kommen.", vocabulary: [],
  }] })),
}))
vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({ t: (key) => key, targetLanguage: "German" }),
}))
vi.mock("../../components/PlayButton", () => ({ default: () => null }))

async function openArticle() {
  render(<MemoryRouter><News /></MemoryRouter>)
  await waitFor(() => expect(screen.getByText("Neues Museum")).toBeInTheDocument())
  fireEvent.click(screen.getByText("Neues Museum"))
  await waitFor(() => expect(screen.getByText("Museum")).toBeInTheDocument())
}

describe("News: sentences to flashcards (3.11.2026)", () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear() })

  it("adds a whole sentence with its translation", async () => {
    const api = await import("../../api/client")
    api.translateWord.mockResolvedValue({ translation: "Muzeum jest nowe." })
    await openArticle()
    fireEvent.click(screen.getByLabelText("Dodaj całe zdanie do fiszek: Das Museum ist neu."))
    await waitFor(() => expect(api.addFlashcard).toHaveBeenCalledWith(42, { word: "Das Museum ist neu.", translation: "Muzeum jest nowe." }))
    expect(api.translateWord).toHaveBeenCalledWith("Das Museum ist neu.", "German", "Polish", 42)
    await waitFor(() => expect(screen.getByText("✓ zdanie")).toBeInTheDocument())
  })

  it("a word keeps its capital letter and gets the sentence as its example", async () => {
    const api = await import("../../api/client")
    api.translateWord.mockResolvedValue({ translation: "muzeum" })
    await openArticle()
    fireEvent.click(screen.getByText("Museum"))
    await waitFor(() => expect(screen.getByText("muzeum")).toBeInTheDocument())
    fireEvent.click(screen.getByText(/Dodaj zaznaczone/))
    await waitFor(() => expect(api.addFlashcard).toHaveBeenCalledWith(42, {
      word: "Museum", translation: "muzeum", example_sentence: "Das Museum ist neu." }))
  })
})
