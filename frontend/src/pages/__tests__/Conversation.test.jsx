import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Conversation from "../Conversation"

vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  startConversation: vi.fn(),
  sendMessageStream: vi.fn(),
  analyzeConversation: vi.fn(),
  askQuestion: vi.fn(),
  getVoiceChatPrompt: vi.fn(),
  analyzePastedConversation: vi.fn(),
  sendVoiceMessage: vi.fn(),
  sendVoiceText: vi.fn(),
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
