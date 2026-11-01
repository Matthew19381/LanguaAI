import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import DailyTest from "../DailyTest"
import { getDailyTest, submitTest, getTestFromErrors } from "../../api/client"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 1),
  getDailyTest: vi.fn(),
  submitTest: vi.fn(),
  getTestFromErrors: vi.fn(),
}))

vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({ t: (key) => key, lang: "pl", targetLanguage: "German" }),
}))

const question = (text) => ({ id: 1, type: "grammar", points: 10, question: text, options: ["A. ja", "B. nein"] })

function renderTest() {
  return render(<MemoryRouter><DailyTest /></MemoryRouter>)
}

describe("DailyTest", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it("sends the errors test as 'errors', not as today's daily test", async () => {
    const user = userEvent.setup()
    getDailyTest.mockResolvedValue({ questions: [question("Pytanie dnia")] })
    submitTest.mockResolvedValueOnce({ score: 0, errors: [{ type: "grammar", question: "q" }] })
    getTestFromErrors.mockResolvedValue({ questions: [question("Pytanie z błędów")] })
    submitTest.mockResolvedValueOnce({ score: 100, errors: [] })
    renderTest()

    await user.click(await screen.findByText("ja"))
    await user.click(screen.getByText("test.submit"))
    await user.click(await screen.findByText("Generuj test z błędów"))
    await user.click(await screen.findByText("ja"))
    expect(screen.getByText("Pytanie z błędów")).toBeInTheDocument()
    await user.click(screen.getByText("test.submit"))

    await waitFor(() => expect(submitTest).toHaveBeenCalledTimes(2))
    expect(submitTest.mock.calls[0][0].test_type).toBe("daily")
    expect(submitTest.mock.calls[1][0].test_type).toBe("errors")
  })

  it("loads the test again after 'try again'", async () => {
    const user = userEvent.setup()
    getDailyTest.mockRejectedValueOnce(new Error("AI service unavailable"))
    getDailyTest.mockResolvedValueOnce({ questions: [question("Pytanie dnia")] })
    renderTest()

    await user.click(await screen.findByText("test.tryAgain"))
    expect(await screen.findByText("Pytanie dnia")).toBeInTheDocument()
    expect(getDailyTest).toHaveBeenCalledTimes(2)
  })
})
