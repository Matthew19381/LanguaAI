import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import LessonQualityNote from "../LessonQualityNote"

describe("LessonQualityNote (A7)", () => {
  it("renders nothing for lessons checked before A7", () => {
    const { container } = render(<LessonQualityNote quality={undefined} />)
    expect(container).toBeEmptyDOMElement()
  })

  it("summarises corrections and open issues, details on click", () => {
    render(<LessonQualityNote quality={{
      review: "ok",
      corrections: [{ path: "grammar.explanation", wrong: "ja kosztuje", correct: "ja kosztuję", reason: "1. osoba" }],
      open_issues: [{ path: "vocabulary.1.word", text: "Brot", issue: "Rzeczownik bez rodzajnika (der/die/das)?" }],
    }} />)
    expect(screen.getByTestId("lesson-quality")).toHaveTextContent("poprawiono 1, 1 do sprawdzenia")
    fireEvent.click(screen.getByRole("button"))
    expect(screen.getByText("ja kosztuję")).toBeInTheDocument()
    expect(screen.getByText(/Brot: Rzeczownik bez rodzajnika/)).toBeInTheDocument()
  })

  it("says plainly when the check failed", () => {
    render(<LessonQualityNote quality={{ review: "failed", corrections: [], open_issues: [] }} />)
    expect(screen.getByTestId("lesson-quality")).toHaveTextContent("nie zadziałała")
  })
})
