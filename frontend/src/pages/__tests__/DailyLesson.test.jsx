import { render, screen } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"
import { describe, it, expect, vi, beforeEach } from "vitest"
import DailyLesson from "../DailyLesson"

// Mock API client - set default return value
vi.mock("../../api/client", () => ({
  getUserId: vi.fn(() => 42),
  getUser: vi.fn(() => Promise.resolve({ native_language: "Polish" })),
  getTodayLesson: vi.fn(() => Promise.resolve(null)),
  completeLesson: vi.fn(() => Promise.resolve({})),
  generateNextLesson: vi.fn(() => Promise.resolve({})),
  evaluateProduction: vi.fn(() => Promise.resolve({})),
  getLesson: vi.fn(() => Promise.resolve({})),
  generateTTS: vi.fn(() => Promise.resolve({})),
  addFlashcardAI: vi.fn(() => Promise.resolve({})),
  generateConceptFlashcards: vi.fn(() => Promise.resolve({ success: true, created: 2, skipped: 0 })),
}))

// Mock useLanguage hook
vi.mock("../../hooks/useLanguage", () => ({
  useLanguage: () => ({
    t: (key) => key,
    lang: "en",
    targetLanguage: "German",
  }),
}))

function renderLesson(initialEntries = ["/lesson"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/lesson" element={<DailyLesson />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("DailyLesson", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem("userId", "42")
  })

  it("renders without crashing", () => {
    renderLesson()
    // If it doesn't crash, test passes
    expect(true).toBe(true)
  })

  it("shows error when lesson is null", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve(null))
    renderLesson()

    const { waitFor } = await import("@testing-library/react")
    await waitFor(() => {
      expect(screen.getByText(/errorTitle/i)).toBeInTheDocument()
    })
  })

  it("SCI-14: shows the grammar elaboration question and reveals the answer on click", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1,
      day_number: 1,
      language: "German",
      is_completed: false,
      content: {
        grammar: {
          topic: "Verb position",
          explanation: "Finite verbs take second position.",
          elaboration_prompt: "Why does the verb move to second position?",
          elaboration_answer: "Because German main clauses are verb-second (V2).",
        },
      },
    }))
    renderLesson()

    const { waitFor, fireEvent } = await import("@testing-library/react")
    await waitFor(() => {
      expect(screen.getByText("Why does the verb move to second position?")).toBeInTheDocument()
    })
    // Answer is hidden until revealed
    expect(screen.queryByText(/verb-second/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("lesson.elaborationReveal"))
    expect(screen.getByText(/verb-second/)).toBeInTheDocument()
  })

  it("SCI-14: hides the elaboration card when the lesson has no elaboration fields", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1,
      day_number: 1,
      language: "German",
      is_completed: false,
      content: {
        grammar: { topic: "Verb position", explanation: "Finite verbs take second position." },
      },
    }))
    renderLesson()

    const { waitFor } = await import("@testing-library/react")
    await waitFor(() => {
      expect(screen.getByText("Finite verbs take second position.")).toBeInTheDocument()
    })
    expect(screen.queryByText("lesson.elaborationTitle")).not.toBeInTheDocument()
  })

  it("matching exercise: splits the model's delimited blob into individual clickable pairs", async () => {
    // The model crams every pair into one item as "a / b" <-> "x | y" (there's
    // no dedicated schema for N pairs) — this must render as separate,
    // matchable rows, not one unsplit blob per column.
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1,
      day_number: 1,
      language: "German",
      is_completed: false,
      content: {
        exercises: [{
          type: "matching",
          instruction: "Match the words",
          items: [{ prompt: "Stuhl / Wohnung", answer: "der Stuhl | die Wohnung" }],
        }],
      },
    }))
    renderLesson()

    const { waitFor, fireEvent } = await import("@testing-library/react")
    // The Exercises section is collapsed by default.
    await waitFor(() => expect(screen.getByText("lesson.exercises (1)")).toBeInTheDocument())
    fireEvent.click(screen.getByText("lesson.exercises (1)"))

    await waitFor(() => {
      expect(screen.getByText("Stuhl")).toBeInTheDocument()
    })
    // Split into individual rows, not one combined "Stuhl / Wohnung" blob.
    expect(screen.queryByText("Stuhl / Wohnung")).not.toBeInTheDocument()
    expect(screen.getByText("Wohnung")).toBeInTheDocument()
    expect(screen.getByText("der Stuhl")).toBeInTheDocument()
    expect(screen.getByText("die Wohnung")).toBeInTheDocument()

    // Clicking the correct pair marks both sides matched.
    fireEvent.click(screen.getByText("Stuhl"))
    fireEvent.click(screen.getByText("der Stuhl"))
    expect(screen.queryByText(/Wszystkie pary połączone/)).not.toBeInTheDocument()
    // Second (last) pair completes the exercise.
    fireEvent.click(screen.getByText("Wohnung"))
    fireEvent.click(screen.getByText("die Wohnung"))
    await waitFor(() => {
      expect(screen.getByText(/Wszystkie pary połączone/)).toBeInTheDocument()
    })
  })

  it("matching exercise: an incorrect pick does not mark either side matched", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1,
      day_number: 1,
      language: "German",
      is_completed: false,
      content: {
        exercises: [{
          type: "matching",
          instruction: "Match the words",
          items: [{ prompt: "Stuhl / Wohnung", answer: "der Stuhl | die Wohnung" }],
        }],
      },
    }))
    renderLesson()

    const { waitFor, fireEvent } = await import("@testing-library/react")
    await waitFor(() => expect(screen.getByText("lesson.exercises (1)")).toBeInTheDocument())
    fireEvent.click(screen.getByText("lesson.exercises (1)"))
    await waitFor(() => expect(screen.getByText("Stuhl")).toBeInTheDocument())

    fireEvent.click(screen.getByText("Stuhl"))
    fireEvent.click(screen.getByText("die Wohnung")) // wrong pair
    expect(screen.getByText("Stuhl")).not.toBeDisabled()
    expect(screen.getByText("die Wohnung")).not.toBeDisabled()
  })

  it("sentence_creation exercise: grades via AI (evaluateProduction), not a substring match", async () => {
    const { getTodayLesson, evaluateProduction } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 7,
      day_number: 1,
      language: "German",
      cefr_level: "A1",
      is_completed: false,
      content: {
        exercises: [{
          type: "sentence_creation",
          instruction: "Ułóż zdanie",
          items: [{ prompt: "Zdanie 1: opisz kogoś", answer: "Przykład: Der Mann ist jung." }],
        }],
      },
    }))
    evaluateProduction.mockResolvedValue({
      success: true, score: 82, feedback: "Dobra praca, drobny błąd rodzajnika.", corrections: [],
    })
    renderLesson()

    const { waitFor, fireEvent } = await import("@testing-library/react")
    await waitFor(() => expect(screen.getByText("lesson.exercises (1)")).toBeInTheDocument())
    fireEvent.click(screen.getByText("lesson.exercises (1)"))
    await waitFor(() => {
      expect(screen.getByPlaceholderText("lesson.yourAnswer")).toBeInTheDocument()
    })
    fireEvent.change(screen.getByPlaceholderText("lesson.yourAnswer"), {
      target: { value: "Die Frau ist alt und die Wohnung ist gross." },
    })
    fireEvent.click(screen.getByText("Sprawdź z AI"))

    await waitFor(() => {
      expect(screen.getByText("82/100")).toBeInTheDocument()
    })
    expect(evaluateProduction).toHaveBeenCalledWith(7, expect.objectContaining({
      user_answer: "Die Frau ist alt und die Wohnung ist gross.",
      instruction: "Ułóż zdanie",
    }))
  })

  it("P1-3: drops exercise items with empty content or answer instead of rendering a blank card", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1,
      day_number: 1,
      language: "German",
      is_completed: false,
      content: {
        exercises: [{
          type: "fill-in-the-blank",
          instruction: "Uzupełnij lukę",
          items: [
            { prompt: "Ich ___ Anna.", answer: "heiße" },   // good — should render
            { prompt: "", answer: "heiße" },                 // empty content — dropped
            { prompt: "Du ___ nett.", answer: "" },          // empty answer — dropped
          ],
        }],
      },
    }))
    renderLesson()

    const { waitFor, fireEvent } = await import("@testing-library/react")
    // Only the one good item counts towards the exercises total.
    await waitFor(() => expect(screen.getByText("lesson.exercises (1)")).toBeInTheDocument())
    fireEvent.click(screen.getByText("lesson.exercises (1)"))

    await waitFor(() => {
      expect(screen.getByText(/Ich ___ Anna\./)).toBeInTheDocument()
    })
    expect(screen.queryByText(/Du ___ nett\./)).not.toBeInTheDocument()
  })

  async function openExercises(exercises) {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1, day_number: 1, language: "German", is_completed: false,
      content: { exercises },
    }))
    renderLesson()
    const { waitFor, fireEvent } = await import("@testing-library/react")
    await waitFor(() => expect(screen.getByText(/^lesson\.exercises \(/)).toBeInTheDocument())
    fireEvent.click(screen.getByText(/^lesson\.exercises \(/))
    await waitFor(() => expect(screen.getByPlaceholderText("lesson.yourAnswer")).toBeInTheDocument())
    return { fireEvent, waitFor }
  }

  it("fill-in-the-blank: a correct answer shows the WHOLE sentence, even with a long ________ blank", async () => {
    const { fireEvent } = await openExercises([{
      type: "fill-in-the-blank", instruction: "Uzupełnij",
      items: [{ prompt: "Ich ________ heute Gemüse. (kaufen)", answer: "kaufe" }],
    }])
    fireEvent.change(screen.getByPlaceholderText("lesson.yourAnswer"), { target: { value: "kaufe" } })
    fireEvent.click(screen.getByText("Sprawdź"))
    expect(screen.getByText("✓ Dobrze!")).toBeInTheDocument()
    // Splitting on exactly "___" used to drop everything after the blank.
    expect(screen.getByText(/heute Gemüse\. \(kaufen\)/)).toBeInTheDocument()
  })

  it("exercise check: a fragment of the answer is no longer accepted as correct", async () => {
    const { fireEvent } = await openExercises([{
      type: "fill-in-the-blank", instruction: "Uzupełnij",
      items: [{ prompt: "Ich ___ heute Gemüse.", answer: "kaufe" }],
    }])
    fireEvent.change(screen.getByPlaceholderText("lesson.yourAnswer"), { target: { value: "e" } })
    fireEvent.click(screen.getByText("Sprawdź"))
    expect(screen.getByText(/Nie do końca/)).toBeInTheDocument()
  })

  it("fill-in-the-blank: revealing the answer counts as wrong and stays locked after hiding it", async () => {
    const { fireEvent } = await openExercises([{
      type: "fill-in-the-blank", instruction: "Uzupełnij",
      items: [{ prompt: "Ich ___ heute Gemüse.", answer: "kaufe" }],
    }])
    const input = screen.getByPlaceholderText("lesson.yourAnswer")
    fireEvent.change(input, { target: { value: "kaufen" } })
    fireEvent.click(screen.getByText("Sprawdź"))
    fireEvent.click(screen.getByText(/lesson\.showExerciseAnswer/))
    fireEvent.click(screen.getByText("lesson.hideExerciseAnswer"))
    // Hidden again, but the wrong answer can't be corrected by copying it.
    expect(input).toBeDisabled()
    expect(screen.getByText(/Podejrzano odpowiedź/)).toBeInTheDocument()
    expect(screen.queryByText("Sprawdź")).not.toBeInTheDocument()
  })

  it("translation: a one-word hint is allowed, a second revealed word counts as wrong", async () => {
    const { fireEvent } = await openExercises([{
      type: "translation", instruction: "Przetłumacz",
      items: [{ prompt: "Kupuję chleb.", answer: "Ich kaufe Brot." }],
    }])
    const input = screen.getByPlaceholderText("lesson.yourAnswer")
    fireEvent.click(screen.getByText("lesson.showExerciseAnswer"))
    expect(input).not.toBeDisabled()
    fireEvent.click(screen.getByText(/lesson\.nextWord.*= błąd/))
    expect(input).toBeDisabled()
    expect(screen.getByText(/Podejrzano odpowiedź/)).toBeInTheDocument()
  })

  it("mixed review: renders backend items that carry a prompt or a question/answer pair", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1, day_number: 2, language: "German", is_completed: false,
      content: {
        interleaved_review: [
          { topic: "Einkaufen", question: "Jak po niemiecku: „gotować”?", answer: "kochen", type: "vocab" },
          { topic: "General", prompt: "Przypomnij sobie 3 słowa z tematu: General", type: "recall" },
        ],
      },
    }))
    renderLesson()
    const { waitFor, fireEvent } = await import("@testing-library/react")
    await waitFor(() => expect(screen.getByText(/^lesson\.mixedReview/)).toBeInTheDocument())
    fireEvent.click(screen.getByText(/^lesson\.mixedReview/))
    expect(screen.getByText("Jak po niemiecku: „gotować”?")).toBeInTheDocument()
    expect(screen.getByText("Przypomnij sobie 3 słowa z tematu: General")).toBeInTheDocument()
    fireEvent.click(screen.getByText("lesson.showAnswer"))
    expect(screen.getByText("kochen")).toBeInTheDocument()
  })

  it("recall (output forcing): an older 5-sentence text is trimmed to 3 sentences", async () => {
    const { getTodayLesson } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1, day_number: 2, language: "German", is_completed: false,
      content: {
        output_forcing: {
          instruction: "Przeczytaj 5 zdań.",
          text: "1. Ich gehe. 2. Du kommst. 3. Er isst. 4. Wir lesen. 5. Ihr schlaft.",
          translation: "1. Idę. 2. Przychodzisz. 3. On je. 4. Czytamy. 5. Śpicie.",
        },
      },
    }))
    renderLesson()
    const { waitFor, fireEvent } = await import("@testing-library/react")
    await waitFor(() => expect(screen.getByText("lesson.outputForcing")).toBeInTheDocument())
    fireEvent.click(screen.getByText("lesson.outputForcing"))
    // 3 sentences × 2 words = 6 hidden words, numbering dropped.
    expect(screen.getByText(/Pokaż słowo \(0\/6\)/)).toBeInTheDocument()
    expect(screen.getByText("Przeczytaj 3 zdań.")).toBeInTheDocument()
  })

  it("vocabulary: shows example_sentence and adds it to flashcards", async () => {
    const { getTodayLesson, addFlashcardAI } = await import("../../api/client")
    getTodayLesson.mockReturnValue(Promise.resolve({
      lesson_id: 1, day_number: 1, language: "German", is_completed: false,
      content: {
        vocabulary: [{ word: "kochen", translation: "gotować", example_sentence: "Ich koche heute Suppe." }],
      },
    }))
    renderLesson()
    const { waitFor, fireEvent } = await import("@testing-library/react")
    await waitFor(() => expect(screen.getByText(/^lesson\.vocabulary/)).toBeInTheDocument())
    if (!screen.queryByText("kochen")) fireEvent.click(screen.getByText(/^lesson\.vocabulary/))
    // Rendered twice: desktop column + the phone line under the translation.
    expect(screen.getAllByText("Ich koche heute Suppe.").length).toBeGreaterThan(0)
    fireEvent.click(screen.getAllByLabelText("lesson.addToFlash")[0])
    await waitFor(() => expect(addFlashcardAI).toHaveBeenCalledWith(42, "Ich koche heute Suppe."))
  })
})
