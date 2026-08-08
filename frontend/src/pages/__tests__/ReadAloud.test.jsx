import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import ReadAloud from "../ReadAloud"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  getReadAloud: vi.fn(),
}))

vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/read-aloud"]}>
      <Routes>
        <Route path="/read-aloud" element={<ReadAloud />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("ReadAloud", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("SCI-12: shows a badge for a lapsed card after reveal", async () => {
    const { getReadAloud } = await import("../../api/client")
    getReadAloud.mockResolvedValue({
      items: [
        { flashcard_id: 1, word: "Verloren", translation: "stracone", lapsed: true },
      ],
    })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/Powiedziałem na głos/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText(/Powiedziałem na głos/))

    expect(screen.getByText(/spróbuj innym sposobem/)).toBeInTheDocument()
    expect(screen.getByText("Verloren")).toBeInTheDocument()
  })

  it("does not show the lapsed badge for a normal card", async () => {
    const { getReadAloud } = await import("../../api/client")
    getReadAloud.mockResolvedValue({
      items: [
        { flashcard_id: 2, word: "Hallo", translation: "cześć", lapsed: false },
      ],
    })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/Powiedziałem na głos/)).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText(/Powiedziałem na głos/))

    expect(screen.queryByText(/spróbuj innym sposobem/)).not.toBeInTheDocument()
    expect(screen.getByText("Hallo")).toBeInTheDocument()
  })
})
