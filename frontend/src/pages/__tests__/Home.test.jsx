import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Home from "../Home"

// Mock API client
vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => null),
  // Pending by default — a test that needs data resolves them itself.
  getStats: vi.fn(() => new Promise(() => {})),
  getDailyTips: vi.fn(() => new Promise(() => {})),
}))

// Mock useLanguage hook
vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({
    t: (key) => key,
    lang: "en",
    targetLanguage: "German",
  }),
}))

function renderHome() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/placement" element={<div>Placement Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("Home", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it("shows welcome screen when no user is logged in", () => {
    renderHome()
    expect(screen.getByText("home.welcomeTitle")).toBeInTheDocument()
    expect(screen.getByText("home.welcomeSubtitle")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /home.startTest/i })).toBeInTheDocument()
  })

  it("navigates to placement when start test is clicked", async () => {
    const user = userEvent.setup()
    renderHome()
    const startLink = screen.getByRole("link", { name: /home.startTest/i })
    await user.click(startLink)
    expect(screen.getByText("Placement Page")).toBeInTheDocument()
  })

  it("shows loading state when user is logged in and data is loading", async () => {
    const { getUserId } = await import("../../api/client")
    getUserId.mockReturnValue(42)
    renderHome()
    expect(screen.getByText("home.loadingDashboard")).toBeInTheDocument()
  })

  it("shows dashboard when user is logged in and data loads", async () => {
    const { getUserId, getStats } = await import("../../api/client")
    getUserId.mockReturnValue(42)
    getStats.mockResolvedValue({
      user: { name: "Test User", target_language: "German", cefr_level: "B1", streak_days: 5, total_xp: 500 },
      lessons: { completed: 10 },
      tests: { average_score: 85 },
      level_info: { level: 10, level_name: "Intermediate", xp: 500, next_level_xp: 1000, progress_percent: 50 },
    })

    renderHome()

    await waitFor(() => {
      expect(screen.getByText(/home.welcomeBack/)).toBeInTheDocument()
    })
    expect(screen.getByText("Test User")).toBeInTheDocument()
    // B1 appears in the level display
    expect(screen.getAllByText(/B1/).length).toBeGreaterThan(0)
  })

  it("displays stat cards when data loads", async () => {
    const { getUserId, getStats } = await import("../../api/client")
    getUserId.mockReturnValue(42)
    getStats.mockResolvedValue({
      user: { name: "Test", streak_days: 3, total_xp: 200 },
      lessons: { completed: 5 },
      tests: { average_score: 75 },
      level_info: { level: 5, level_name: "Beginner", xp: 200, next_level_xp: 500, progress_percent: 40 },
    })

    renderHome()

    await waitFor(() => {
      expect(screen.getByText("home.dayStreak")).toBeInTheDocument()
    })
    expect(screen.getByText("home.totalXP")).toBeInTheDocument()
    expect(screen.getByText("home.lessonsDone")).toBeInTheDocument()
    expect(screen.getByText("home.avgScore")).toBeInTheDocument()
  })

  it("displays quick action cards", async () => {
    const { getUserId, getStats } = await import("../../api/client")
    getUserId.mockReturnValue(42)
    getStats.mockResolvedValue({
      user: { name: "Test", cefr_level: "A2" },
      level_info: { level: 3, xp: 100, next_level_xp: 300, progress_percent: 33 },
    })

    renderHome()

    await waitFor(() => {
      expect(screen.getByText("home.todayLesson")).toBeInTheDocument()
    })
    expect(screen.getByText("home.dailyTest")).toBeInTheDocument()
    expect(screen.getByText("home.practiceSpeaking")).toBeInTheDocument()
  })

  it("shows the dashboard without waiting for the AI tips", async () => {
    const { getUserId, getStats, getDailyTips } = await import("../../api/client")
    getUserId.mockReturnValue(42)
    getStats.mockResolvedValue({
      user: { name: "Test", cefr_level: "A2" },
      level_info: { level: 3, xp: 100, next_level_xp: 300, progress_percent: 33 },
    })
    getDailyTips.mockReturnValue(new Promise(() => {}))  // AI still generating

    renderHome()

    await waitFor(() => {
      expect(screen.getByText("home.todayLesson")).toBeInTheDocument()
    })
    expect(screen.queryByText("home.loadingDashboard")).not.toBeInTheDocument()
  })

  it("displays tips when available", async () => {
    const { getUserId, getStats, getDailyTips } = await import("../../api/client")
    getUserId.mockReturnValue(42)
    getStats.mockResolvedValue({
      user: { name: "Test", cefr_level: "B1" },
      level_info: { level: 10, xp: 500, next_level_xp: 1000, progress_percent: 50 },
    })
    getDailyTips.mockResolvedValue({
      tips: [
        { type: "grammar", title: "Tip 1", content: "Content 1" },
        { type: "vocabulary", title: "Tip 2", content: "Content 2" },
      ]
    })

    renderHome()

    await waitFor(() => {
      expect(screen.getByText("home.dailyTips")).toBeInTheDocument()
    })
    expect(screen.getByText("Tip 1")).toBeInTheDocument()
    expect(screen.getByText("Tip 2")).toBeInTheDocument()
  })
})
