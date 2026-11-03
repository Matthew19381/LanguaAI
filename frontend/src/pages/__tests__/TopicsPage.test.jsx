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
        <Route path="/flashcards" element={<div>Flashcards page</div>} />
        <Route path="/practice" element={<div>Practice page</div>} />
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

describe("TopicsPage — Hierarchia -> 'Przećwicz fiszki' link (Wariant D)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("links a topic node to a flashcard session scoped to that topic", async () => {
    const { getTopicHierarchy } = await import("../../api/client")
    getTopicHierarchy.mockResolvedValue({
      topics: [{
        id: 9, name: "Jedzenie", category: "vocabulary", mastery_percent: 40,
        is_due: false, days_until_review: 3, items_count: 2, has_own_items: true,
        subtopics: [],
      }],
    })
    renderPage()

    await waitFor(() => expect(screen.getByText("Hierarchia")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Hierarchia"))
    await waitFor(() => expect(screen.getByText("Jedzenie")).toBeInTheDocument())

    const link = screen.getByTitle("Przećwicz fiszki z tego tematu")
    expect(link).toHaveAttribute("href", "/flashcards?topic_id=9&topic_name=Jedzenie")
  })
})

describe("TopicsPage — Bank wiedzy entry", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("shows the rule, plan, mastery and own errors instead of topic review stats", async () => {
    const { getTopicHierarchy, getTopicDetail } = await import("../../api/client")
    getTopicHierarchy.mockResolvedValue({
      topics: [{
        id: 1, name: "Bank wiedzy · Szyk zdania i zdania złożone", category: "grammar", mastery_percent: 0,
        is_due: false, days_until_review: 0, items_count: 0, has_own_items: false, group_mastery_percent: 0,
        subtopics: [
          { id: 2, name: "Szyk V2 [G-V2]", skill_id: "G-V2", category: "grammar", mastery_percent: 0, is_due: false, days_until_review: 0, items_count: 1, has_own_items: true, subtopics: [] },
        ],
      }],
    })
    getTopicDetail.mockResolvedValue({
      topic: { id: 2, name: "Szyk V2 [G-V2]", memory_strength: 0, repetitions: 0, interval: 0, difficulty: 5, stability: 0, is_due: false },
      items: [],
      knowledge: {
        skill_id: "G-V2", skill_name: "Szyk V2", group: "Szyk zdania i zdania złożone",
        rule: "Czasownik stoi na 2. miejscu.",
        examples: [{ de: "Heute gehe ich ins Kino.", pl: "Dziś idę do kina." }],
        typical_errors: ["„Heute ich gehe”"],
        plan: { modules: ["M00"], days: [{ day: 1, module_id: "M00", done: true, repair: false },
                                         { day: 15, module_id: "M00", done: false, repair: true }], next_day: 15 },
        mastery: { status: "slaba", accuracy: 0.2, attempts: 5, correct_days: 1 },
        recent_errors: [{ wrong: "Heute ich gehe", correct: "Heute gehe ich", source: "exercise" }],
        exercises: 4,
      },
    })
    renderPage()

    await waitFor(() => expect(screen.getByText("Hierarchia")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Hierarchia"))
    await waitFor(() => expect(screen.getByText("Szyk zdania i zdania złożone")).toBeInTheDocument())
    expect(screen.queryByText(/^Bank wiedzy · /)).not.toBeInTheDocument()     // prefix hidden
    fireEvent.click(screen.getByText("Szyk zdania i zdania złożone"))
    await waitFor(() => expect(screen.getByText("Szyk V2 [G-V2]")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Szyk V2 [G-V2]"))

    await waitFor(() => expect(screen.getByTestId("knowledge-entry")).toBeInTheDocument())
    expect(screen.getByText("Czasownik stoi na 2. miejscu.")).toBeInTheDocument()
    expect(screen.getByText("Heute gehe ich ins Kino.")).toBeInTheDocument()
    expect(screen.getByText(/15 \(powtórka naprawcza\)/)).toBeInTheDocument()
    expect(screen.getByText(/Słaba: wróci w rozgrzewce/)).toBeInTheDocument()
    expect(screen.getByText("Heute gehe ich")).toBeInTheDocument()
    const headings = screen.getAllByRole("heading", { level: 4 }).map(h => h.textContent)
    expect(headings.indexOf("Twoje błędy")).toBe(2)                      // own errors right after the rule
    expect(screen.getByText("Częste błędy Polaków (ogólne, nie twoje)")).toBeInTheDocument()
    expect(screen.queryByText("Siła zapamiętania")).not.toBeInTheDocument()
    expect(screen.queryByText("Stabilność")).not.toBeInTheDocument()
  })
})

describe("TopicsPage — Bank wiedzy (3.11.2026)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
    localStorage.setItem("userLanguage", "German")
  })

  it("sends the language with every call (without it every skill was at 0 %)", async () => {
    const api = await import("../../api/client")
    renderPage()
    await waitFor(() => expect(api.getTopicStats).toHaveBeenCalled())
    expect(api.getTopics).toHaveBeenCalledWith(42, expect.objectContaining({ language: "German" }))
    expect(api.getTopicTree).toHaveBeenCalledWith(42, "German")
    expect(api.getTopicHierarchy).toHaveBeenCalledWith(42, "German")
    expect(api.getDueTopics).toHaveBeenCalledWith(42, "German")
    expect(api.getTopicStats).toHaveBeenCalledWith(42, "German")
  })

  it("a skill to review shows why, and its detail offers practising just that skill", async () => {
    const api = await import("../../api/client")
    api.getTopics.mockResolvedValue({ topics: [{
      id: 5, skill_id: "G-V2", name: "Szyk V2 [G-V2]", category: "grammar", description: "Czasownik na 2. miejscu",
      memory_strength: 0.6, is_due: true, review_reason: "ćwiczenia do powtórki: 2",
      mastery: { status: "slaba", accuracy: 0.6, attempts: 8 }, items_count: 0,
    }] })
    api.getTopicDetail.mockResolvedValue({
      topic: { id: 5, name: "Szyk V2 [G-V2]", memory_strength: 0.6 }, items: [],
      knowledge: { skill_id: "G-V2", group: "Szyk", rule: "V2", examples: [], recent_errors: [], typical_errors: [],
        plan: { days: [], modules: [], foundation: false }, mastery: { status: "slaba", accuracy: 0.6, attempts: 8, correct_days: 1 },
        exercises: 4 },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText("ćwiczenia do powtórki: 2")).toBeInTheDocument())
    expect(screen.getByText("8 prób")).toBeInTheDocument()
    fireEvent.click(screen.getByText("ćwiczenia do powtórki: 2"))
    await waitFor(() => expect(screen.getByTestId("practice-skill-button")).toBeInTheDocument())
    fireEvent.click(screen.getByTestId("practice-skill-button"))
    await waitFor(() => expect(screen.getByText("Practice page")).toBeInTheDocument())
  })
})
