import { render, screen, waitFor } from "@testing-library/react"
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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/flashcards"]}>
      <Routes>
        <Route path="/flashcards" element={<Flashcards />} />
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
