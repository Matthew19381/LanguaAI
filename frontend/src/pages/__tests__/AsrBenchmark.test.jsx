import { render, screen, fireEvent, waitFor, act } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import AsrBenchmark from "../AsrBenchmark"

vi.mock("../../api/client", () => ({
  getAsrSentences: vi.fn(),
  uploadAsrRecording: vi.fn(),
  evaluateAsr: vi.fn(),
  getLatestAsr: vi.fn(),
}))

class FakeRecorder {
  constructor() { this.state = "inactive" }
  start() { this.state = "recording" }
  stop() {
    this.state = "inactive"
    this.ondataavailable?.({ data: new Blob(["x"]) })
    this.onstop?.()
  }
}

let lastRecognition
class FakeRecognition {
  constructor() { lastRecognition = this }
  start() {}
  stop() { this.onend?.() }
}

const result = {
  measured_at: "2026-10-27T10:00:00+00:00", recordings: 2, recommended_whisper: "base",
  rule: "najmniejszy model z WER do 2.0 pkt od najlepszego i najwyżej 3.0 s na zdanie",
  results: {
    browser: { wer: 12.5, avg_seconds: null, sentences: 2 },
    tiny: { wer: 20.0, avg_seconds: 0.8, sentences: 2 },
    base: { wer: 10.0, avg_seconds: 1.2, sentences: 2 },
    small: { wer: null, error: "download blocked", avg_seconds: null, sentences: 0 },
  },
}

describe("AsrBenchmark (A6)", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    localStorage.clear()
    const api = await import("../../api/client")
    api.getAsrSentences.mockResolvedValue({ sentences: ["Ich bin müde.", "Wir gehen."], current_whisper: "tiny" })
    api.getLatestAsr.mockResolvedValue({ result: null })
    api.uploadAsrRecording.mockResolvedValue({ saved: 0, recordings: 1 })
    window.MediaRecorder = FakeRecorder
    navigator.mediaDevices = { getUserMedia: vi.fn(() => Promise.resolve({ getTracks: () => [{ stop() {} }] })) }
  })
  afterEach(() => {
    delete window.SpeechRecognition
    vi.useRealTimers()
  })

  it("records a sentence with what the browser heard and moves on", async () => {
    window.SpeechRecognition = FakeRecognition
    const api = await import("../../api/client")
    render(<MemoryRouter><AsrBenchmark /></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId("asr-sentence")).toHaveTextContent("Ich bin müde."))

    fireEvent.click(screen.getByTestId("asr-record"))
    await waitFor(() => expect(screen.getByTestId("asr-stop")).toBeInTheDocument())
    act(() => lastRecognition.onresult({ resultIndex: 0, results: [Object.assign([{ transcript: " ich bin müde " }], { isFinal: true })] }))
    vi.useFakeTimers()
    fireEvent.click(screen.getByTestId("asr-stop"))
    await act(async () => { await vi.advanceTimersByTimeAsync(1600) })
    vi.useRealTimers()

    await waitFor(() => expect(api.uploadAsrRecording).toHaveBeenCalled())
    const form = api.uploadAsrRecording.mock.calls[0][0]
    expect(form.get("index")).toBe("0")
    expect(form.get("browser_text")).toBe("ich bin müde")
    expect(form.get("session_id")).toMatch(/^[A-Za-z0-9-]{8,64}$/)
    await waitFor(() => expect(screen.getByTestId("asr-sentence")).toHaveTextContent("Wir gehen."))
    expect(screen.getByTestId("asr-progress")).toHaveTextContent("1 / 2")
    expect(JSON.parse(localStorage.getItem("asr_benchmark_session")).done).toEqual([0])
  })

  it("sends no browser text when the browser cannot recognise speech", async () => {
    const api = await import("../../api/client")
    render(<MemoryRouter><AsrBenchmark /></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId("asr-record")).toBeInTheDocument())
    expect(screen.getByText(/zmierzony zostanie tylko Whisper/)).toBeInTheDocument()
    fireEvent.click(screen.getByTestId("asr-record"))
    await waitFor(() => expect(screen.getByTestId("asr-stop")).toBeInTheDocument())
    vi.useFakeTimers()
    fireEvent.click(screen.getByTestId("asr-stop"))
    await act(async () => { await vi.advanceTimersByTimeAsync(1600) })
    vi.useRealTimers()
    await waitFor(() => expect(api.uploadAsrRecording).toHaveBeenCalled())
    expect(api.uploadAsrRecording.mock.calls[0][0].has("browser_text")).toBe(false)
  })

  it("evaluates and shows WER, errors and the recommended model", async () => {
    localStorage.setItem("asr_benchmark_session", JSON.stringify({ id: "abcdef12-3456", done: [0, 1] }))
    const api = await import("../../api/client")
    api.evaluateAsr.mockResolvedValue(result)
    render(<MemoryRouter><AsrBenchmark /></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId("asr-evaluate")).not.toBeDisabled())
    fireEvent.click(screen.getByTestId("asr-evaluate"))
    await waitFor(() => expect(screen.getByTestId("asr-result")).toBeInTheDocument())
    expect(api.evaluateAsr).toHaveBeenCalledWith("abcdef12-3456")
    expect(screen.getByTestId("asr-row-browser")).toHaveTextContent("12.5 %")
    expect(screen.getByTestId("asr-row-small")).toHaveTextContent("błąd")
    expect(screen.getByText(/Whisper small: download blocked/)).toBeInTheDocument()
    expect(screen.getByTestId("asr-recommendation")).toHaveTextContent("base")
    expect(screen.getByTestId("asr-recommendation")).toHaveTextContent("WHISPER_MODEL=base")
  })

  it("shows the last saved result and keeps evaluation off without recordings", async () => {
    const api = await import("../../api/client")
    api.getLatestAsr.mockResolvedValue({ result })
    render(<MemoryRouter><AsrBenchmark /></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId("asr-result")).toBeInTheDocument())
    expect(screen.getByTestId("asr-evaluate")).toBeDisabled()
  })
})
