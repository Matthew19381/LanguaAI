import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Conversation from "../Conversation"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  startConversation: vi.fn(),
  getConversationModuleTask: vi.fn(() => Promise.resolve({ module_task: null })),
  sendMessageStream: vi.fn(),
  analyzeConversation: vi.fn(),
  askQuestion: vi.fn(),
  getVoiceChatPrompt: vi.fn(),
  analyzePastedConversation: vi.fn(),
  generateTTS: vi.fn(() => Promise.resolve({ url: "/audio/tts_x.mp3" })),
}))

vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({ t: (key) => key, targetLanguage: "German" }),
}))

// jsdom doesn't implement scrollIntoView; Conversation.jsx calls it whenever
// the message list changes.
Element.prototype.scrollIntoView = vi.fn()

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/conversation"]}>
      <Routes>
        <Route path="/conversation" element={<Conversation />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

async function startChat() {
  const { startConversation } = await import("../../api/client")
  startConversation.mockResolvedValue({
    session_id: "sess-1",
    scenario: "Everyday conversation",
    ai_role: "partner",
    user_role: "learner",
    suggested_phrases: [],
    opening_line: "Hallo!",
  })
  renderPage()
  fireEvent.click(screen.getByText("conv.start"))
  await waitFor(() => expect(screen.getByText("Hallo!")).toBeInTheDocument())
}

describe("Conversation — streamed replies (P2-2)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("grows the assistant bubble chunk by chunk as deltas arrive, then settles on the final text", async () => {
    const { sendMessageStream } = await import("../../api/client")
    sendMessageStream.mockImplementation(async (sessionId, text, userId, onDelta) => {
      onDelta("Hallo")
      onDelta(", wie")
      onDelta(" geht's?")
      return { response: "Hallo, wie geht's?", message_count: 3 }
    })
    await startChat()

    fireEvent.change(screen.getByPlaceholderText("conv.typeMessage"), { target: { value: "Ich lerne Deutsch." } })
    fireEvent.keyDown(screen.getByPlaceholderText("conv.typeMessage"), { key: "Enter" })

    await waitFor(() => {
      expect(screen.getByText("Hallo, wie geht's?")).toBeInTheDocument()
    })
    expect(sendMessageStream).toHaveBeenCalledWith("sess-1", "Ich lerne Deutsch.", undefined, expect.any(Function))
  })

  it("keeps a partial reply visible if the stream errors after some text arrived", async () => {
    const { sendMessageStream } = await import("../../api/client")
    sendMessageStream.mockImplementation(async (sessionId, text, userId, onDelta) => {
      onDelta("Hallo")
      throw new Error("upstream broke")
    })
    await startChat()

    fireEvent.change(screen.getByPlaceholderText("conv.typeMessage"), { target: { value: "Hi" } })
    fireEvent.keyDown(screen.getByPlaceholderText("conv.typeMessage"), { key: "Enter" })

    await waitFor(() => {
      expect(screen.getByText("Hallo")).toBeInTheDocument()
    })
    // No generic error bubble was added on top of the partial text.
    expect(screen.queryByText("conv.errorResponse")).not.toBeInTheDocument()
  })

  it("shows a generic error bubble if the stream fails before any text arrived", async () => {
    const { sendMessageStream } = await import("../../api/client")
    sendMessageStream.mockRejectedValue(new Error("network down"))
    await startChat()

    fireEvent.change(screen.getByPlaceholderText("conv.typeMessage"), { target: { value: "Hi" } })
    fireEvent.keyDown(screen.getByPlaceholderText("conv.typeMessage"), { key: "Enter" })

    await waitFor(() => {
      expect(screen.getByText("conv.errorResponse")).toBeInTheDocument()
    })
  })
})

describe("Conversation — module task and voice mode (2026-10-26)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("offers today's module task and starts the conversation with it", async () => {
    const { getConversationModuleTask, startConversation } = await import("../../api/client")
    getConversationModuleTask.mockResolvedValue({ module_task: {
      day_number: 10, day_type_pl: "zadanie mówione", task: "Opowiedz o swoim dniu",
      topic: "Opowiedz o swoim dniu", target_structures: ["Perfekt"],
    } })
    startConversation.mockResolvedValue({
      session_id: "sess-2", scenario: "Rozmowa z kolegą", ai_role: "kolega", user_role: "ty",
      suggested_phrases: [], opening_line: "Na, wie war dein Tag?", task: "Opowiedz o swoim dniu",
      target_structures: ["Perfekt"],
    })
    renderPage()
    await waitFor(() => expect(screen.getByTestId("module-task")).toBeInTheDocument())
    expect(screen.getByText("Opowiedz o swoim dniu")).toBeInTheDocument()
    expect(screen.getByText(/Perfekt/)).toBeInTheDocument()
    fireEvent.click(screen.getByText("conv.moduleTaskStart"))
    await waitFor(() => expect(screen.getByText("Na, wie war dein Tag?")).toBeInTheDocument())
    expect(startConversation).toHaveBeenCalledWith(42, "everyday conversation", true)
    expect(screen.getByText(/conv.moduleTaskYours/)).toBeInTheDocument()
  })

  it("hides the module task card without a plan task", async () => {
    const { getConversationModuleTask } = await import("../../api/client")
    getConversationModuleTask.mockResolvedValue({ module_task: null })
    renderPage()
    await waitFor(() => expect(screen.getByText("conv.start")).toBeInTheDocument())
    expect(screen.queryByTestId("module-task")).not.toBeInTheDocument()
  })

  it("sends spoken turns through the session and reads the reply aloud", async () => {
    const { sendMessageStream, generateTTS } = await import("../../api/client")
    sendMessageStream.mockResolvedValue({ response: "Wirklich? Wohin bist du gegangen?", message_count: 3 })
    const played = vi.fn()
    globalThis.Audio = vi.fn(function (url) { this.url = url; this.play = played })
    class FakeRecognition {
      start() { FakeRecognition.last = this }
      stop() {}
    }
    window.SpeechRecognition = FakeRecognition
    await startChat()

    fireEvent.click(screen.getByText("🔇 Voice OFF"))
    fireEvent.click(screen.getByTitle("Rozpocznij nagrywanie"))
    FakeRecognition.last.onresult({ results: [[{ transcript: "Ich habe ins Kino gegangen" }]] })

    await waitFor(() => expect(played).toHaveBeenCalled())
    expect(sendMessageStream).toHaveBeenCalledWith("sess-1", "Ich habe ins Kino gegangen", undefined, expect.any(Function))
    expect(generateTTS).toHaveBeenCalledWith("Wirklich? Wohin bist du gegangen?", "German")
    expect(globalThis.Audio).toHaveBeenCalledWith("/audio/tts_x.mp3")
    delete window.SpeechRecognition
  })
})
