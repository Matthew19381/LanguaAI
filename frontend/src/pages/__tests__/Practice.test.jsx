import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Practice from "../Practice"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  getPracticeSet: vi.fn(() => Promise.resolve({
    exercises: [{ id: 1, prompt: "Heute ___ ich im Büro.", exercise_type: "fill-in-the-blank", skill_tag: "G-V2" }],
    due_count: 1, interleaved_count: 0, weak_skills: [], generated_new: 0,
  })),
  answerExercise: vi.fn(),
  generateExerciseVariants: vi.fn(),
  getExerciseStats: vi.fn(() => Promise.resolve({})),
  getOfflinePack: vi.fn(() => Promise.resolve({ exercises: [] })),
}))
vi.mock("../../hooks/useLanguage", () => ({ useLanguage: () => ({ t: (k) => k, targetLanguage: "German" }) }))
vi.mock("../../hooks/useOfflineSync", () => ({
  useOfflineSync: () => ({ pending: 0, syncing: false, lastSynced: null, sync: vi.fn(), refresh: vi.fn() }),
}))

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes><Route path="/practice" element={<Practice />} /></Routes>
    </MemoryRouter>
  )
}

describe("Practice — one Bank wiedzy skill (3.11.2026)", () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear() })

  it("asks only for that skill's exercises and says so", async () => {
    const { getPracticeSet } = await import("../../api/client")
    renderAt("/practice?skill=G-V2&name=Szyk%20V2")
    await waitFor(() => expect(screen.getByTestId("practice-skill")).toHaveTextContent("Szyk V2"))
    expect(getPracticeSet).toHaveBeenCalledWith(42, { size: 10, skill: "G-V2" })
  })

  it("without a skill the mixed set is asked for as before", async () => {
    const { getPracticeSet } = await import("../../api/client")
    renderAt("/practice")
    await waitFor(() => expect(getPracticeSet).toHaveBeenCalled())
    expect(getPracticeSet).toHaveBeenCalledWith(42, { size: 10, includeNew: false })
    expect(screen.queryByTestId("practice-skill")).not.toBeInTheDocument()
  })
})
