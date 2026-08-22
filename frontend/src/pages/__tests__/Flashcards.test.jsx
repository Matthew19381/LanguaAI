import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Flashcards from "../Flashcards"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  getFlashcards: vi.fn(() => Promise.resolve({ flashcards: [], total: 0 })),
  getDueFlashcards: vi.fn(() => Promise.resolve({ due_cards: [] })),
  getFlashcardOfflinePack: vi.fn(() => Promise.resolve({ flashcards: [] })),
  reviewFlashcard: vi.fn(() => Promise.resolve({})),
  exportAnki: vi.fn(() => Promise.resolve({})),
  addFlashcard: vi.fn(() => Promise.resolve({})),
  addFlashcardAI: vi.fn(() => Promise.resolve({})),
  bulkImportFlashcards: vi.fn(() => Promise.resolve({})),
  getFlashcardAltContext: vi.fn(() => Promise.resolve({ success: true, sentence: "", translation: "" })),
}))

vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({ t: (key) => key, targetLanguage: "German" }),
}))

vi.mock("../../hooks/useOfflineSync", () => ({
  useOfflineSync: () => ({ pending: 0, syncing: false, lastSynced: null, sync: vi.fn(), refresh: vi.fn() }),
}))

vi.mock("../../utils/offlineQueue", () => ({
  saveCardPack: vi.fn(() => true),
  loadCardPack: vi.fn(() => null),
  enqueueFlashcardReview: vi.fn(),
}))

function renderPage(initialEntry = "/flashcards") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/flashcards" element={<Flashcards />} />
        <Route path="/lesson/:lessonId" element={<div>Lesson page</div>} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("Flashcards — SCI-13 mnemonic", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("shows the keyword mnemonic for a card that has one", async () => {
    // Front and back are both mounted at once (CSS-only flip via a `flipped`
    // class), so the mnemonic is present in the document regardless of flip
    // state — it just isn't visually facing the user until they flip the card.
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{
        id: 1, word: "Angst", translation: "fear", language: "German",
        mnemonic: "Like 'angst' in English — a jolt of dread.",
      }],
    })
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByText("Angst").length).toBeGreaterThan(0)
    })
    expect(screen.getByText(/jolt of dread/)).toBeInTheDocument()
  })

  it("shows no mnemonic hint for a card without one", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 2, word: "Tisch", translation: "table", language: "German", mnemonic: null }],
    })
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByText("Tisch").length).toBeGreaterThan(0)
    })
    expect(screen.queryByText("💡", { exact: false })).not.toBeInTheDocument()
  })
})

describe("Flashcards — session summary (P2-1)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("shows a progress bar while reviewing the due queue", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [
        { id: 1, word: "Angst", translation: "fear", language: "German" },
        { id: 2, word: "Tisch", translation: "table", language: "German" },
      ],
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Angst").length).toBeGreaterThan(0))
    // 2 due cards, 0 reviewed yet -> counter shows the starting state.
    expect(screen.getByText("1 / 2")).toBeInTheDocument()
  })

  it("shows the end-of-session summary with a rating breakdown once every due card is rated", async () => {
    const { getDueFlashcards, reviewFlashcard } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Angst", translation: "fear", language: "German" }],
    })
    reviewFlashcard.mockResolvedValue({})
    renderPage()

    await waitFor(() => expect(screen.getAllByText("Angst").length).toBeGreaterThan(0))
    fireEvent.click(screen.getByText("flash.reveal"))
    await waitFor(() => expect(screen.getByText("flash.easy")).toBeInTheDocument())
    fireEvent.click(screen.getByText("flash.easy"))

    await waitFor(() => {
      expect(screen.getByText("flash.sessionDoneTitle")).toBeInTheDocument()
    })
    expect(reviewFlashcard).toHaveBeenCalledWith(1, 4, 42)
    // Exactly one "Easy" rating given this session.
    expect(screen.getByText("1")).toBeInTheDocument()
  })

  it("'browse cards' dismisses the summary so the reviewed card can be revisited", async () => {
    const { getDueFlashcards, reviewFlashcard } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Angst", translation: "fear", language: "German" }],
    })
    reviewFlashcard.mockResolvedValue({})
    renderPage()

    await waitFor(() => expect(screen.getAllByText("Angst").length).toBeGreaterThan(0))
    fireEvent.click(screen.getByText("flash.reveal"))
    await waitFor(() => expect(screen.getByText("flash.good")).toBeInTheDocument())
    fireEvent.click(screen.getByText("flash.good"))
    await waitFor(() => expect(screen.getByText("flash.sessionDoneTitle")).toBeInTheDocument())

    fireEvent.click(screen.getByText("flash.browseCards"))
    expect(screen.queryByText("flash.sessionDoneTitle")).not.toBeInTheDocument()
    expect(screen.getAllByText("Angst").length).toBeGreaterThan(0)
  })
})

describe("Flashcards — Wariant B+D (kontekst/produkcja + integracja z lekcjami)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("cloze mode shows the example sentence with the word blanked instead of the bare word", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{
        id: 1, word: "Brot", translation: "bread", language: "German",
        example_sentence: "Ich kaufe frisches Brot.",
      }],
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))

    fireEvent.click(screen.getByText("flash.clozeMode"))
    // Front shows the blanked sentence. The back (always mounted, CSS-only
    // flip) still reveals the bare word — cloze only hides it before reveal.
    await waitFor(() => {
      expect(screen.getByText("Ich kaufe frisches ___.")).toBeInTheDocument()
    })
  })

  it("cloze mode falls back to the plain word when the card has no matching example sentence", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Brot", translation: "bread", language: "German", example_sentence: null }],
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))

    fireEvent.click(screen.getByText("flash.clozeMode"))
    // Still shows the bare word — nothing to blank out.
    expect(screen.getAllByText("Brot").length).toBeGreaterThan(0)
  })

  it("shows a 'Zobacz w lekcji' link for a card linked to a lesson, and not otherwise", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Brot", translation: "bread", language: "German", lesson_id: 7 }],
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))
    const link = screen.getByText("flash.viewInLesson").closest("a")
    expect(link).toHaveAttribute("href", "/lesson/7")
  })

  it("does not show a lesson link when the card has no lesson_id", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Brot", translation: "bread", language: "German" }],
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))
    expect(screen.queryByText("flash.viewInLesson")).not.toBeInTheDocument()
  })

  it("shows the topic-filter banner from ?topic_id=&topic_name= and passes topic_id to the API", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({ due_cards: [] })
    renderPage("/flashcards?topic_id=5&topic_name=Jedzenie")

    await waitFor(() => {
      expect(screen.getByText("flash.topicFilterActive")).toBeInTheDocument()
    })
    expect(getDueFlashcards).toHaveBeenCalledWith(42, "5")

    fireEvent.click(screen.getByText("flash.clearTopicFilter"))
    await waitFor(() => {
      expect(screen.queryByText("flash.topicFilterActive")).not.toBeInTheDocument()
    })
  })

  it("typed-answer mode: correct input flips the card and shows the correct banner", async () => {
    const { getDueFlashcards, reviewFlashcard } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Brot", translation: "bread", language: "German", fsrs_state: "Relearning" }],
    })
    reviewFlashcard.mockResolvedValue({})
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))

    const input = screen.getByPlaceholderText("flash.typeTranslation")
    fireEvent.change(input, { target: { value: "bread" } })
    fireEvent.click(screen.getByText("flash.check"))

    await waitFor(() => expect(screen.getByText("flash.typedCorrect")).toBeInTheDocument())
    // Card is flipped -> rating buttons are showing.
    expect(screen.getByText("flash.easy")).toBeInTheDocument()
  })

  it("typed-answer mode: wrong input shows the incorrect banner, not the correct one", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Brot", translation: "bread", language: "German", fsrs_state: "Relearning" }],
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))

    fireEvent.change(screen.getByPlaceholderText("flash.typeTranslation"), { target: { value: "totally wrong" } })
    fireEvent.click(screen.getByText("flash.check"))

    await waitFor(() => expect(screen.getByText("flash.typedIncorrect")).toBeInTheDocument())
  })

  it("does not show the typed-answer panel for a card that isn't struggling", async () => {
    const { getDueFlashcards } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Brot", translation: "bread", language: "German", fsrs_state: "Review" }],
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))
    expect(screen.queryByPlaceholderText("flash.typeTranslation")).not.toBeInTheDocument()
  })

  it("'see it in another context' fetches and displays an alternate sentence for a struggling card", async () => {
    const { getDueFlashcards, getFlashcardAltContext } = await import("../../api/client")
    getDueFlashcards.mockResolvedValue({
      due_cards: [{ id: 1, word: "Brot", translation: "bread", language: "German", fsrs_state: "Relearning" }],
    })
    getFlashcardAltContext.mockResolvedValue({
      success: true, sentence: "Wir essen Brot beim Picknick.", translation: "Jemy chleb na pikniku.",
    })
    renderPage()
    await waitFor(() => expect(screen.getAllByText("Brot").length).toBeGreaterThan(0))
    fireEvent.click(screen.getByText("flash.reveal"))

    await waitFor(() => expect(screen.getByText("flash.altContextButton")).toBeInTheDocument())
    fireEvent.click(screen.getByText("flash.altContextButton"))

    await waitFor(() => {
      expect(screen.getByText("Wir essen Brot beim Picknick.")).toBeInTheDocument()
    })
    expect(getFlashcardAltContext).toHaveBeenCalledWith(1, 42)
  })
})
