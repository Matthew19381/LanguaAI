import { render, screen } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import DailyLesson from "../DailyLesson"

// Mock API client - set default return value
vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  getTodayLesson: vi.fn(() => Promise.resolve(null)),
  completeLesson: vi.fn(() => Promise.resolve({})),
  generateNextLesson: vi.fn(() => Promise.resolve({})),
  evaluateProduction: vi.fn(() => Promise.resolve({})),
  getLesson: vi.fn(() => Promise.resolve({})),
  generateTTS: vi.fn(() => Promise.resolve({})),
}))

// Mock useLanguage hook
vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({
    t: (key) => key,
    lang: "en",
    targetLanguage: "German",
  }),
}))

function renderLesson(initialEntries = ["/lesson"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/lesson" element={<DailyLesson />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("DailyLesson", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("renders without crashing", () => {
    renderLesson()
    // If it doesn't crash, test passes
    expect(true).toBe(true)
  })

  it("shows error when lesson is null", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve(null))
    renderLesson()
    
    const { waitFor } = await import("@testing-library/react")
    await waitFor(() => {
      expect(screen.getByText(/errorTitle/i)).toBeInTheDocument()
    })
  })
})
