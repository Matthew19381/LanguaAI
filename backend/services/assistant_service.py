"""Assistant service — in-app AI assistant (docs/ASYSTENT_AI_SPEC.md, D-2/D-4).

Single function `answer_assistant_question`, wired to the existing
`gemini_service.generate_text` via `@with_model("assistant")` — same pattern
as every other AI-generating function in this codebase (`conversation.py`'s
`_ai_conversation_reply`/`_ai_translate`). No RAG: the whole domain knowledge
is a short, hand-curated cheat sheet (docs/ASSISTANT_CONTEXT.md, ~2-3 KB)
injected into the system prompt on every call, per D-2.
"""
import logging
import os

from backend.services.gemini_service import generate_text, with_model

logger = logging.getLogger(__name__)

_CONTEXT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs",
    "ASSISTANT_CONTEXT.md",
)

_FALLBACK_CONTEXT = (
    "LinguaAI — aplikacja do nauki niemieckiego z algorytmem powtórek FSRS. "
    "(Uwaga: pełny plik docs/ASSISTANT_CONTEXT.md nie został znaleziony — "
    "odpowiadaj ogólnie i przyznaj się, jeśli nie znasz szczegółu.)"
)

# Cached at import time — the cheat sheet is hand-curated and only changes
# with a deploy, so there's no need to hit disk on every request.
_cached_context: str | None = None


def _load_context() -> str:
    global _cached_context
    if _cached_context is not None:
        return _cached_context
    try:
        with open(_CONTEXT_PATH, encoding="utf-8") as f:
            _cached_context = f.read()
    except OSError as e:
        logger.warning("ASSISTANT_CONTEXT.md not found (%s) — using fallback context", e)
        _cached_context = _FALLBACK_CONTEXT
    return _cached_context


def _format_optional(value) -> str:
    return value if value else "brak"


def build_assistant_prompt(
    question: str,
    route: str | None,
    cefr_level: str,
    element_context: dict | None,
    selected_text: str | None,
) -> str:
    """Build the full prompt: role + cheat sheet + runtime context + question.
    Shape matches docs/ASYSTENT_AI_SPEC.md §3."""
    context_md = _load_context()

    if element_context:
        parts = []
        for key in ("tag", "text", "aria_label", "nearest_heading", "testid"):
            val = element_context.get(key) if isinstance(element_context, dict) else getattr(element_context, key, None)
            if val:
                parts.append(f"{key}={val!r}")
        element_str = ", ".join(parts) if parts else "brak"
    else:
        element_str = "brak"

    return f"""[ROLA] Jesteś asystentem AI wbudowanym w LinguaAI — aplikację do nauki
niemieckiego z algorytmem FSRS v6. Odpowiadasz PO POLSKU, krótko i konkretnie.

[WIEDZA O SYSTEMIE]
{context_md}

[KONTEKST BIEŻĄCY]
- Użytkownik jest na stronie: {_format_optional(route)}
- Poziom CEFR użytkownika: {_format_optional(cefr_level)}
- Wskazany element: {element_str}
- Zaznaczony tekst: {_format_optional(selected_text)}

[PYTANIE UŻYTKOWNIKA] {question}

[ZASADY]
- Jeśli pytanie dotyczy słownictwa/gramatyki niemieckiego → odpowiadaj jak
  nauczyciel, ale nie odmawiaj — pomóż jeśli się da.
- Jeśli pytanie dotyczy działania aplikacji (ten ekran/przycisk/liczba) →
  wyjaśnij zwięźle, odwołując się do wskazanego elementu.
- Nie znasz odpowiedzi / brak w kontekście → powiedz to wprost, nie zgaduj.
- Nigdy nie ujawniaj kluczy API, danych innych użytkowników, wewnętrznych ID
  bazy danych."""


@with_model("assistant")
async def _ai_assistant_answer(prompt: str) -> str:
    return await generate_text(prompt)


async def answer_assistant_question(
    question: str,
    route: str | None = None,
    cefr_level: str = "A2",
    element_context: dict | None = None,
    selected_text: str | None = None,
) -> str:
    """Answer a user question about the LinguaAI app itself (D-2/D-3).
    Raises whatever the underlying AI call raises — the router decides how
    to surface that (graceful degradation message), same pattern as every
    other AI-calling router function in this codebase."""
    prompt = build_assistant_prompt(
        question=question,
        route=route,
        cefr_level=cefr_level,
        element_context=element_context,
        selected_text=selected_text,
    )
    answer = await _ai_assistant_answer(prompt)
    return answer.strip()
