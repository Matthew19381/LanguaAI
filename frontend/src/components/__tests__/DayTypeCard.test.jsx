import { render, screen, fireEvent, act } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi, afterEach } from "vitest"
import DayTypeCard from "../DayTypeCard"

function renderCard(props) {
  return render(<MemoryRouter><DayTypeCard moduleId="M01" moduleTask="Opowiedz o swoim dniu" {...props} /></MemoryRouter>)
}

describe("DayTypeCard (A3)", () => {
  afterEach(() => {
    vi.useRealTimers()
    delete window.SpeechRecognition
  })

  it("renders nothing for lessons without a programme day", () => {
    const { container } = renderCard({ dayType: undefined })
    expect(container).toBeEmptyDOMElement()
  })

  it.each([
    ["zadanie_mowione", "/conversation"],
    ["probny_egzamin", "/exam"],
    ["test_bledy", "/test"],
    ["naprawa", "/topics"],
  ])("%s links to its screen", (dayType, href) => {
    renderCard({ dayType })
    expect(screen.getByTestId("day-type-card").querySelector(`a[href="${href}"]`)).not.toBeNull()
  })

  it("fluency day runs 90/60/45 s rounds and counts the words spoken", async () => {
    vi.useFakeTimers()
    let instance
    window.SpeechRecognition = class {
      constructor() { instance = this }
      start() {}
      stop() {}
    }
    renderCard({ dayType: "plynnosc" })
    expect(screen.getByText("Opowiedz o swoim dniu")).toBeInTheDocument()
    fireEvent.click(screen.getByTestId("fluency-start"))
    expect(screen.getByTestId("fluency-left")).toHaveTextContent("90 s")
    act(() => {
      instance.onresult({ resultIndex: 0, results: [Object.assign([{ transcript: "Ich stehe um sieben Uhr auf" }], { isFinal: true })] })
    })
    for (let i = 0; i < 90; i++) await act(async () => { vi.advanceTimersByTime(1000) })
    await act(async () => { vi.advanceTimersByTime(1500) })
    expect(screen.getByTestId("fluency-results")).toHaveTextContent("Runda 1: 6 słów, 4 słów na minutę")
    expect(screen.getByTestId("fluency-start")).toHaveTextContent("Runda 2: 60 s")
  })
})
