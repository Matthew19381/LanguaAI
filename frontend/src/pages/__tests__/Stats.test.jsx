import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi } from "vitest"
import Stats from "../Stats"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  getStats: vi.fn(() => Promise.resolve({
    user: { name: "Anna", total_xp: 100, level: "A2", streak_days: 1 },
    lessons: { total: 1, completed: 1, recent: [] },
    tests: { total: 0, average_score: 0, recent: [] },
    flashcards: { total: 0, due: 0 },
  })),
  getDailyTips: vi.fn(() => Promise.resolve({ tips: [] })),
  getStudyPlan: vi.fn(() => Promise.resolve(null)),
  getLessonConcepts: vi.fn(() => Promise.resolve({ concepts: [] })),
  generateConceptFlashcards: vi.fn(),
  getBestStudyTime: vi.fn(() => Promise.resolve(null)),
  exportProgressCSV: vi.fn(),
}))

vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({ t: (key) => key, targetLanguage: "German" }),
}))

describe("Stats (3.11.2026)", () => {
  it("has no 'Prompt dla Voice Chat' section", async () => {
    const { getStats } = await import("../../api/client")
    render(<MemoryRouter><Stats /></MemoryRouter>)
    await waitFor(() => expect(getStats).toHaveBeenCalled())
    await waitFor(() => expect(screen.queryByText(/loading|Ładowanie/i)).not.toBeInTheDocument())
    expect(screen.queryByText(/Voice Chat/i)).not.toBeInTheDocument()
    expect(screen.queryByText("stats.voiceChatPrompt")).not.toBeInTheDocument()
    expect(screen.queryByText("Wygeneruj prompt")).not.toBeInTheDocument()
  })
})
