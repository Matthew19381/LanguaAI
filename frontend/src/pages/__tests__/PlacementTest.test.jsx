import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import PlacementTest from "../PlacementTest"

// Mock API client
vi.mock("../../api/client", () => ({
  createUser: vi.fn(),
  getUser: vi.fn(),
  startPlacementTest: vi.fn(),
  submitPlacementTest: vi.fn(),
  setUserId: vi.fn(),
  getUserId: vi.fn(() => null),
}))

// Mock useLanguage hook
vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({
    t: (key) => key,
    lang: "en",
    targetLanguage: "German",
  }),
}))

function renderPlacement(initialEntries = ["/placement"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/placement" element={<PlacementTest />} />
        <Route path="/" element={<div>Home Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("PlacementTest", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    localStorage.clear()   // the finished test saves userName there
    const { getUserId } = await import("../../api/client")
    getUserId.mockReturnValue(null)
  })

  it("without an account on this device tells how to sign in instead", () => {
    renderPlacement()
    expect(screen.getByTestId("placement-have-account")).toHaveTextContent("Pokaż link logowania")
  })

  it("signed in: re-levels the same account and never creates a new one", async () => {
    const { createUser, getUser, getUserId, startPlacementTest, submitPlacementTest, setUserId } =
      await import("../../api/client")
    const user = userEvent.setup()
    getUserId.mockReturnValue(1)
    getUser.mockResolvedValue({ user_id: 1, name: "Mateusz", target_language: "German" })
    startPlacementTest.mockResolvedValue({
      questions: [{ id: "q1", question: "Q1?", options: ["A. Yes", "B. No"], type: "grammar", cefr_hint: "A1" }]
    })
    submitPlacementTest.mockResolvedValue({ cefr_level: "A2", score: 60, strong_areas: [], weak_areas: [] })
    renderPlacement()
    expect(await screen.findByTestId("placement-account")).toHaveTextContent("Mateusz")
    expect(screen.queryByPlaceholderText("place.namePlaceholder")).not.toBeInTheDocument()
    expect(screen.queryByTestId("placement-have-account")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /place.startTest/i }))
    await screen.findByText("Q1?")
    await user.click(screen.getByText("Yes"))
    await user.click(screen.getByRole("button", { name: /place.submit/i }))
    await waitFor(() => expect(submitPlacementTest).toHaveBeenCalled())
    expect(createUser).not.toHaveBeenCalled()
    expect(submitPlacementTest.mock.calls[0][0]).toMatchObject({ user_id: 1, language: "German" })
    await user.click(await screen.findByRole("button", { name: /place.startLearning/i }))
    expect(setUserId).toHaveBeenCalledWith(1)
  })

  it("a stale saved id (account gone) falls back to a new account", async () => {
    const { getUser, getUserId } = await import("../../api/client")
    getUserId.mockReturnValue(99)
    getUser.mockRejectedValue(new Error("User not found"))
    renderPlacement()
    await waitFor(() => expect(getUser).toHaveBeenCalledWith(99))
    expect(screen.getByPlaceholderText("place.namePlaceholder")).toBeInTheDocument()
  })

  it("renders setup step with form fields", () => {
    renderPlacement()
    expect(screen.getByText("place.title")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("place.namePlaceholder")).toBeInTheDocument()
    expect(screen.getAllByRole("combobox").length).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: /place.startTest/i })).toBeInTheDocument()
  })

  it("shows error when starting test without name", async () => {
    const user = userEvent.setup()
    renderPlacement()
    const startButton = screen.getByRole("button", { name: /place.startTest/i })
    await user.click(startButton)
    expect(screen.getByText("place.enterName")).toBeInTheDocument()
  })

  it("starts test when form is filled", async () => {
    const { createUser, startPlacementTest } = await import("../../api/client")
    const user = userEvent.setup()
    createUser.mockResolvedValue({ user_id: 42 })
    startPlacementTest.mockResolvedValue({
      questions: [
        { id: "q1", question: "What is this?", options: ["A. Yes", "B. No"], type: "grammar", cefr_hint: "A1" }
      ]
    })
    renderPlacement()
    const nameInput = screen.getByPlaceholderText("place.namePlaceholder")
    await user.type(nameInput, "Test User")
    const startButton = screen.getByRole("button", { name: /place.startTest/i })
    await user.click(startButton)
    await waitFor(() => {
      expect(createUser).toHaveBeenCalledWith({
        name: "Test User",
        native_language: "Polish",
        target_language: "German",
      })
    })
  })

  it("shows questions after test starts", async () => {
    const { createUser, startPlacementTest } = await import("../../api/client")
    const user = userEvent.setup()
    createUser.mockResolvedValue({ user_id: 42 })
    startPlacementTest.mockResolvedValue({
      questions: [
        { id: "q1", question: "What is this?", options: ["A. Yes", "B. No"], type: "grammar", cefr_hint: "A1" }
      ]
    })
    renderPlacement()
    await user.type(screen.getByPlaceholderText("place.namePlaceholder"), "Test User")
    await user.click(screen.getByRole("button", { name: /place.startTest/i }))
    await waitFor(() => {
      expect(screen.getByText("What is this?")).toBeInTheDocument()
    })
  })

  it("allows selecting an answer", async () => {
    const { createUser, startPlacementTest } = await import("../../api/client")
    const user = userEvent.setup()
    createUser.mockResolvedValue({ user_id: 42 })
    startPlacementTest.mockResolvedValue({
      questions: [
        { id: "q1", question: "Q1?", options: ["A. Yes", "B. No"], type: "grammar", cefr_hint: "A1" }
      ]
    })
    renderPlacement()
    await user.type(screen.getByPlaceholderText("place.namePlaceholder"), "Test User")
    await user.click(screen.getByRole("button", { name: /place.startTest/i }))
    await waitFor(() => {
      expect(screen.getByText("Q1?")).toBeInTheDocument()
    })
    const optionA = screen.getByText("Yes")
    await user.click(optionA)
    expect(screen.getByText("A")).toBeInTheDocument()
  })

  it("submits test and shows results", async () => {
    const { createUser, startPlacementTest, submitPlacementTest } = await import("../../api/client")
    const user = userEvent.setup()
    createUser.mockResolvedValue({ user_id: 42 })
    startPlacementTest.mockResolvedValue({
      questions: [
        { id: "q1", question: "Q1?", options: ["A. Yes", "B. No"], type: "grammar", cefr_hint: "A1" }
      ]
    })
    submitPlacementTest.mockResolvedValue({
      cefr_level: "A1",
      score: 100,
      strong_areas: ["grammar"],
      weak_areas: [],
      recommendations: "Good job!",
      study_plan: { language: "German", cefr_level: "A1", daily_topics: [] }
    })
    renderPlacement()
    await user.type(screen.getByPlaceholderText("place.namePlaceholder"), "Test User")
    await user.click(screen.getByRole("button", { name: /place.startTest/i }))
    await waitFor(() => {
      expect(screen.getByText("Q1?")).toBeInTheDocument()
    })
    await user.click(screen.getByText("Yes"))
    await user.click(screen.getByRole("button", { name: /place.submit/i }))
    await waitFor(() => {
      expect(screen.getByText(/place.yourLevel/i)).toBeInTheDocument()
    })
    expect(screen.getByText("A1")).toBeInTheDocument()
  })

  it("displays error message on API failure", async () => {
    const { createUser } = await import("../../api/client")
    const user = userEvent.setup()
    createUser.mockRejectedValue(new Error("Network Error"))
    renderPlacement()
    await user.type(screen.getByPlaceholderText("place.namePlaceholder"), "Test User")
    await user.click(screen.getByRole("button", { name: /place.startTest/i }))
    await waitFor(() => {
      expect(screen.getByText("Network Error")).toBeInTheDocument()
    })
  })
})
