import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Exam from "../Exam"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  startExam: vi.fn(),
  getExam: vi.fn(),
  getExamHistory: vi.fn(),
  sendExamTeil1: vi.fn(),
  finishExamTeil1: vi.fn(),
  submitExamTeil2: vi.fn(),
  submitExamTeil3: vi.fn(),
  scoreExam: vi.fn(),
  generateTTS: vi.fn(() => Promise.resolve({ url: null })),
}))

const tasks = {
  teil1: { situation: "Feier planen", points: ["Wann?", "Wo?", "Essen?", "Geschenk?"], partner_opening: "Hallo!" },
  teil2: { topics: [{ title: "Handy für Kinder?" }, { title: "Homeoffice?" }] },
  teil3: { partner_presentation: { title: "Sport", text: "Mein Thema ist Sport." } },
}
const base = {
  exam_id: 7, status: "teil1", prep_minutes: 15, teil1_max_turns: 12, slides: ["s1", "s2", "s3", "s4", "s5"],
  tasks, teil1_history: [{ role: "assistant", content: "Hallo!" }], teil2_topic: null, teil2_transcript: null,
  teil3: null, score: null,
}
const noGoal = { exams: [], goal: { reached: false, pass_percent: 60, last_two: [] }, unfinished_exam_id: null }
const score = {
  percent: 75, points: 63, max_points: 84, passed: true,
  parts: { teil3: { erfuellung: { points: 12, max: 16, levels: ["B", "B"], reason: "Dobra odpowiedź", errors: ["ich habe gegangen → ich bin gegangen"] } } },
}

describe("Exam (mock Goethe B1 Sprechen)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("goes through prep, the three parts and shows the score", async () => {
    const api = await import("../../api/client")
    api.getExamHistory.mockResolvedValue(noGoal)
    api.startExam.mockResolvedValue(base)
    api.sendExamTeil1.mockResolvedValue({ reply: "Gut, am Samstag.", turns_left: 11 })
    api.finishExamTeil1.mockResolvedValue({ ...base, status: "teil2" })
    api.submitExamTeil2.mockResolvedValue({ ...base, status: "teil3", teil3: { question: "Warum?", answer: null, feedback: null } })
    api.submitExamTeil3.mockResolvedValue({ ...base, status: "scoring", teil3: { question: "Warum?" } })
    api.scoreExam.mockResolvedValue({ ...base, status: "scored", score })

    render(<MemoryRouter><Exam /></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId("exam-goal")).toBeInTheDocument())
    fireEvent.click(screen.getByTestId("exam-start"))
    await waitFor(() => expect(screen.getByTestId("exam-prep")).toBeInTheDocument())
    fireEvent.click(screen.getByText("Homeoffice?"))
    fireEvent.click(screen.getByTestId("exam-prep-done"))

    fireEvent.change(screen.getByTestId("exam-teil1-input"), { target: { value: "Am Samstag?" } })
    fireEvent.click(screen.getByTestId("exam-teil1-send"))
    await waitFor(() => expect(screen.getByText("Gut, am Samstag.")).toBeInTheDocument())
    expect(api.sendExamTeil1).toHaveBeenCalledWith(7, 42, "Am Samstag?")
    fireEvent.click(screen.getByTestId("exam-teil1-finish"))

    await waitFor(() => expect(screen.getByTestId("exam-teil2")).toBeInTheDocument())
    fireEvent.change(screen.getByTestId("exam-teil2-input"), { target: { value: "Mein Thema ist Homeoffice." } })
    fireEvent.click(screen.getByTestId("exam-teil2-submit"))
    // The topic chosen during preparation is the one submitted
    await waitFor(() => expect(api.submitExamTeil2).toHaveBeenCalledWith(7, 42, 1, "Mein Thema ist Homeoffice."))

    await waitFor(() => expect(screen.getByTestId("exam-teil3-question")).toHaveTextContent("Warum?"))
    fireEvent.change(screen.getByTestId("exam-teil3-answer"), { target: { value: "Weil es praktisch ist." } })
    fireEvent.change(screen.getByTestId("exam-teil3-feedback"), { target: { value: "Danke! Machst du oft Sport?" } })
    fireEvent.click(screen.getByTestId("exam-teil3-submit"))

    // Scoring starts by itself after Teil 3
    await waitFor(() => expect(screen.getByTestId("exam-results")).toBeInTheDocument())
    expect(api.submitExamTeil3).toHaveBeenCalledWith(7, 42, "Weil es praktisch ist.", "Danke! Machst du oft Sport?")
    expect(api.scoreExam).toHaveBeenCalledTimes(1)
    expect(screen.getByText("75%")).toBeInTheDocument()
    expect(screen.getByText("ich habe gegangen → ich bin gegangen")).toBeInTheDocument()
  })

  it("shows the goal as reached after two passes and offers to resume", async () => {
    const api = await import("../../api/client")
    api.getExamHistory.mockResolvedValue({
      exams: [{ exam_id: 2, scored_at: "2026-12-01T10:00:00", percent: 64, passed: true },
              { exam_id: 1, scored_at: "2026-11-01T10:00:00", percent: 61, passed: true }],
      goal: { reached: true, pass_percent: 60, last_two: [64, 61] }, unfinished_exam_id: 3,
    })
    render(<MemoryRouter><Exam /></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId("exam-goal")).toHaveTextContent("osiągnięty"))
    expect(screen.getByText("Dokończ rozpoczęty")).toBeInTheDocument()
    expect(screen.getByTestId("exam-history")).toHaveTextContent("64%")
  })
})
