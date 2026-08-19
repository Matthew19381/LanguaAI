import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import TopicsPage from "../TopicsPage"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  getTopics: vi.fn(() => Promise.resolve({ topics: [] })),
  getTopicTree: vi.fn(() => Promise.resolve({ tree: {} })),
  getTopicHierarchy: vi.fn(() => Promise.resolve({ topics: [] })),
  getDueTopics: vi.fn(() => Promise.resolve({ topics: [] })),
  getTopicStats: vi.fn(() => Promise.resolve({})),
  getTopicDetail: vi.fn(() => Promise.resolve({
    topic: { id: 1, name: "Perfekt", memory_strength: 0.5, repetitions: 0, interval: 0, difficulty: 5, stability: 0, is_due: false },
    items: [],
  })),
  reviewTopic: vi.fn(() => Promise.resolve({})),
  generateFlashcardsFromTopic: vi.fn(),
  generateFlashcardsFromErrors: vi.fn(),
  batchAddFlashcards: vi.fn(),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/topics"]}>
      <Routes>
        <Route path="/topics" element={<TopicsPage />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("TopicsPage — Hierarchia tab (P2-4)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("shows an empty state when there is no hierarchy data", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Hierarchia")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Hierarchia"))
    await waitFor(() => {
      expect(screen.getByText(/Brak tematów/)).toBeInTheDocument()
    })
  })

  it("renders a root topic with subtopics collapsed, expands to reveal them with mastery %", async () => {
    const { getTopicHierarchy } = await import("../../api/client")
    getTopicHierarchy.mockResolvedValue({
      topics: [{
        id: 1, name: "Czasy przeszłe", category: "grammar", description: null,
        cefr_level: "A2", mastery_percent: 0, is_due: false, days_until_review: 0,
        items_count: 0, has_own_items: false, group_mastery_percent: 60,
        subtopics: [
          { id: 2, name: "Perfekt", category: "grammar", mastery_percent: 80, is_due: false, days_until_review: 5, items_count: 3, has_own_items: true, subtopics: [] },
          { id: 3, name: "Präteritum", category: "grammar", mastery_percent: 40, is_due: true, days_until_review: -1, items_count: 2, has_own_items: true, subtopics: [] },
        ],
      }],
    })
    renderPage()

    await waitFor(() => expect(screen.getByText("Hierarchia")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Hierarchia"))

    await waitFor(() => expect(screen.getByText("Czasy przeszłe")).toBeInTheDocument())
    // Group mastery shown for the collapsed parent, children not yet in the DOM.
    expect(screen.getByText("60%")).toBeInTheDocument()
    expect(screen.queryByText("Perfekt")).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("Czasy przeszłe"))

    await waitFor(() => expect(screen.getByText("Perfekt")).toBeInTheDocument())
    expect(screen.getByText("Präteritum")).toBeInTheDocument()
    expect(screen.getByText("80%")).toBeInTheDocument()
    expect(screen.getByText("40%")).toBeInTheDocument()
    // The lapsed/stale subtopic surfaces its "due" badge in the tree, not just
    // in a separate due-list tab.
    expect(screen.getByTitle("Temat wystygł — czas na powtórkę podstaw")).toBeInTheDocument()
  })

  it("clicking a leaf subtopic opens its TopicDetail panel", async () => {
    const { getTopicHierarchy, getTopicDetail } = await import("../../api/client")
    getTopicHierarchy.mockResolvedValue({
      topics: [{
        id: 1, name: "Czasy przeszłe", category: "grammar", mastery_percent: 0,
        is_due: false, days_until_review: 0, items_count: 0, has_own_items: false,
        group_mastery_percent: 50,
        subtopics: [
          { id: 2, name: "Perfekt", category: "grammar", mastery_percent: 50, is_due: false, days_until_review: 5, items_count: 3, has_own_items: true, subtopics: [] },
        ],
      }],
    })
    renderPage()

    await waitFor(() => expect(screen.getByText("Hierarchia")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Hierarchia"))
    await waitFor(() => expect(screen.getByText("Czasy przeszłe")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Czasy przeszłe"))
    await waitFor(() => expect(screen.getByText("Perfekt")).toBeInTheDocument())

    fireEvent.click(screen.getByText("Perfekt"))
    await waitFor(() => expect(getTopicDetail).toHaveBeenCalledWith(2))
  })
})
