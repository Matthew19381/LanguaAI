"""
Model Router — wybiera odpowiedni model w zależności od typu zadania i dostawcy.

Dostępne tier'y:
  "free"  — darmowe modele (:free suffix), limity 20 req/min, 200 req/day
  "cheap" — tanie płatne modele (<$1/1M tokens), brak limitów dziennych
  "best"  — najlepsze modele jakościowo, wyższy koszt

Domyślny tier ustawia się przez settings.AI_MODEL_TIER (domyślnie "cheap").
"""

from backend.config import settings

# ═══════════════════════════════════════════════════════════════════════════════
# OPENROUTER MODEL CATALOG (May 2026)
# Format: "model_id"  # context | category | tier | notes
# ═══════════════════════════════════════════════════════════════════════════════

OPENROUTER_MODELS = {
    # ── FREE TIER (:free suffix) ─────────────────────────────────────────────
    "openrouter/owl-alpha":                    "1.0M | agentic  | free | tools, long-context",
    "inclusionai/ring-2.6-1t:free":            "262K | reasoning | free | 1T params, tools",
    "google/gemma-4-26b-a4b-it:free":         "262K | multimodal| free | vision+tools",
    "google/gemma-4-31b-it:free":              "262K | multimodal| free | vision+tools",
    "arcee-ai/trinity-large-thinking:free":    "262K | reasoning | free | thinking, tools",
    "nvidia/nemotron-3-super-120b-a12b:free": "262K | reasoning | free | MoE, tools",
    "qwen/qwen3-next-80b-a3b-instruct:free":   "262K | instruct  | free | MoE, tools",
    "qwen/qwen3-coder:free":                  "262K | coding    | free | best free coding",
    "deepseek/deepseek-v4-flash:free":         "256K | general   | free | programming, reasoning",
    "minimax/minimax-m2.5:free":               "197K | general   | free | strong generalist",
    "openai/gpt-oss-120b:free":                "131K | general   | free | OpenAI open-weight",
    "openai/gpt-oss-20b:free":                 "131K | general   | free | OpenAI open-weight, fast",
    "z-ai/glm-4.5-air:free":                   "131K | general   | free | tools, fast",
    "meta-llama/llama-3.2-3b-instruct:free":   "131K | general   | free | lightweight",
    "meta-llama/llama-3.3-70b-instruct:free":  "66K  | general   | free | tools, Meta",
    "nousresearch/hermes-3-llama-3.1-405b:free": "131K | general | free | 405B params",
    "liquid/lfm-2.5-1.2b-instruct:free":       "33K  | general   | free | tiny, fast",
    "liquid/lfm-2.5-1.2b-thinking:free":       "33K  | reasoning | free | thinking, tiny",

    # ── CHEAP TIER (tanie płatne, <$1/1M tokens) ────────────────────────────
    "deepseek/deepseek-v3.2":                  "128K | reasoning | cheap | ~90% GPT-5 jakości, 1/50 kosztu",
    "deepseek/deepseek-v3.2-non-thinking":     "128K | general   | cheap | szybszy, tańszy",
    "qwen/qwen3-235b-a22b":                    "128K | instruct  | cheap | Alibaba hybrid arch",
    "qwen/qwen3-coder":                        "256K | coding    | cheap | najlepszy coding w taniej cenie",
    "qwen/qwen3-8b":                           "128K | general   | cheap | szybki, tani",
    "mistralai/mistral-small-3.1-24b":         "128K | general   | cheap | Mistral, szybki",
    "mistralai/mistral-small-3.1-8b":          "128K | general   | cheap | Mistral, najtańszy",
    "meta-llama/llama-4-maverick-17b":         "128K | general   | cheap | Meta multimodal",
    "meta-llama/llama-4-scout-17b":            "128K | general   | cheap | Meta, szybki",
    "openai/gpt-4o-mini":                      "128K | general   | cheap | OpenAI, tani",
    "openai/gpt-4o":                           "128K | general   | cheap | OpenAI, jakościowy",
    "google/gemini-2.0-flash":                 "128K | general   | cheap | Google, szybki",
    "google/gemini-2.5-flash":                 "128K | general   | cheap | Google, najnowszy flash",
    "google/gemini-2.5-flash-lite":            "128K | general   | cheap | Google, najtańszy",
    "minimax/minimax-m2.5":                    "197K | general   | cheap | MiniMax, strong generalist",
    "minimax/minimax-m2.7":                    "197K | general   | cheap | MiniMax, top usage",
    "x-ai/grok-3-mini":                        "128K | general   | cheap | X.ai, szybki",
    "amazon/nova-lite-v1":                     "128K | general   | cheap | Amazon, tani",
    "amazon/nova-micro-v1":                    "128K | general   | cheap | Amazon, najtańszy",

    # ── BEST TIER (najlepsze jakościowo) ─────────────────────────────────────
    "anthropic/claude-sonnet-4-6":             "200K | general   | best | Anthropic, top quality",
    "anthropic/claude-opus-4-6":               "200K | general   | best | Anthropic, najlepszy",
    "openai/gpt-5":                            "128K | general   | best | OpenAI flagship",
    "openai/gpt-5-mini":                       "128K | general   | best | OpenAI, tani flagship",
    "google/gemini-2.5-pro":                   "128K | general   | best | Google flagship",
    "google/gemini-3.1-pro":                   "128K | general   | best | Google, top usage",
    "deepseek/deepseek-r1":                    "128K | reasoning | best | DeepSeek reasoning",
    "x-ai/grok-3":                             "128K | general   | best | X.ai flagship",
    "qwen/qwen3-max":                          "128K | general   | best | Alibaba flagship",
    "mistralai/mistral-large-2":               "128K | general   | best | Mistral flagship",
}

# ── Tier lookup sets ────────────────────────────────────────────────────────
FREE_MODELS = {k for k, v in OPENROUTER_MODELS.items() if "| free " in v}
CHEAP_MODELS = {k for k, v in OPENROUTER_MODELS.items() if "| cheap " in v}
BEST_MODELS = {k for k, v in OPENROUTER_MODELS.items() if "| best " in v}


def get_model_for_task(task: str, fallback: str = None, tier: str = None) -> str:
    """
    Zwróć nazwę modelu dla danego typu zadania, dostawcy i tieru.

    Args:
        task: Typ zadania — 'placement', 'lesson', 'conversation', 'news',
              'pronunciation', 'test', 'code', 'reasoning', 'multimodal'
        fallback: Model dla nieznanego taska (domyślnie zależy od providera)
        tier: 'free', 'cheap', 'best' — nadpisuje settings.AI_MODEL_TIER

    Returns:
        Nazwa modelu (np. 'deepseek/deepseek-v3.2' dla openrouter
        lub 'gemini-2.0-flash' dla gemini direct)
    """
    provider = settings.AI_PROVIDER.lower()
    effective_tier = (tier or getattr(settings, 'AI_MODEL_TIER', 'cheap')).lower()

    if provider == "gemini":
        return _get_gemini_model(task, fallback, effective_tier)
    else:
        return _get_openrouter_model(task, fallback, effective_tier)


def _get_openrouter_model(task: str, fallback: str = None, tier: str = "cheap") -> str:
    """
    Zwróć model OpenRouter dla danego zadania i tieru.

    Strategia:
    - lesson/conversation/news → jakościowy model z długim kontekstem
    - placement/pronunciation → szybki, tani model
    - test/code/reasoning → specjalistyczny model
    """
    if fallback is None:
        fallback = _tier_default_openrouter(tier)

    # Mapping per tier: task → model
    MAPPINGS = {
        "free": {
            "placement":     "meta-llama/llama-3.2-3b-instruct:free",
            "pronunciation": "liquid/lfm-2.5-1.2b-instruct:free",
            "lesson":        "deepseek/deepseek-v4-flash:free",
            "conversation":  "minimax/minimax-m2.5:free",
            "news":          "google/gemma-4-26b-a4b-it:free",
            "test":          "deepseek/deepseek-v4-flash:free",
            "code":          "qwen/qwen3-coder:free",
            "reasoning":     "nvidia/nemotron-3-super-120b-a12b:free",
            "multimodal":    "google/gemma-4-26b-a4b-it:free",
        },
        "cheap": {
            "placement":     "deepseek/deepseek-v3.2-non-thinking",
            "pronunciation": "google/gemini-2.5-flash",
            "lesson":        "deepseek/deepseek-v3.2-non-thinking",
            "conversation":  "deepseek/deepseek-v3.2-non-thinking",
            "news":          "google/gemini-2.5-flash",
            "test":          "deepseek/deepseek-v3.2-non-thinking",
            "code":          "qwen/qwen3-coder",
            "reasoning":     "deepseek/deepseek-v3.2",
            "multimodal":    "google/gemini-2.5-flash",
        },
        "best": {
            "placement":     "openai/gpt-5-mini",
            "pronunciation": "google/gemini-2.5-flash",
            "lesson":        "anthropic/claude-sonnet-4-6",
            "conversation":  "anthropic/claude-sonnet-4-6",
            "news":          "google/gemini-2.5-pro",
            "test":          "openai/gpt-5",
            "code":          "openai/gpt-5",
            "reasoning":     "deepseek/deepseek-r1",
            "multimodal":    "google/gemini-3.1-pro",
        },
    }

    mapping = MAPPINGS.get(tier, MAPPINGS["cheap"])
    return mapping.get(task, fallback)


def _get_gemini_model(task: str, fallback: str = None, tier: str = "cheap") -> str:
    """Zwróć model Gemini Direct API dla danego zadania i tieru."""
    if fallback is None:
        fallback = "gemini-2.0-flash"

    MAPPINGS = {
        "free": {
            # Gemini Direct API — używamy najtańszych dostępnych modeli
            # (Gemini nie ma :free suffix jak OpenRouter)
            "placement":     "gemini-2.0-flash-lite",
            "pronunciation": "gemini-2.0-flash-lite",
            "lesson":        "gemini-2.0-flash-lite",
            "conversation":  "gemini-2.0-flash-lite",
            "news":          "gemini-2.0-flash-lite",
            "test":          "gemini-2.0-flash-lite",
            "code":          "gemini-2.0-flash",
            "reasoning":     "gemini-2.0-flash",
            "multimodal":    "gemini-2.0-flash-lite",
        },
        "cheap": {
            "placement":     "gemini-2.0-flash-lite",
            "pronunciation": "gemini-2.0-flash-lite",
            "lesson":        "gemini-2.0-flash",
            "conversation":  "gemini-2.0-flash",
            "news":          "gemini-2.0-flash",
            "test":          "gemini-2.0-flash",
            "code":          "gemini-2.0-pro",
            "reasoning":     "gemini-2.0-pro",
            "multimodal":    "gemini-2.0-flash",
        },
        "best": {
            "placement":     "gemini-2.5-flash",
            "pronunciation": "gemini-2.5-flash",
            "lesson":        "gemini-2.5-pro",
            "conversation":  "gemini-2.5-pro",
            "news":          "gemini-2.5-pro",
            "test":          "gemini-2.5-pro",
            "code":          "gemini-2.5-pro",
            "reasoning":     "gemini-2.5-pro",
            "multimodal":    "gemini-2.5-pro",
        },
    }

    mapping = MAPPINGS.get(tier, MAPPINGS["cheap"])
    return mapping.get(task, fallback)


def _tier_default_openrouter(tier: str) -> str:
    """Domyślny fallback model dla danego tieru OpenRouter."""
    return {
        "free":  "meta-llama/llama-3.2-3b-instruct:free",
        "cheap": "deepseek/deepseek-v3.2-non-thinking",
        "best":  "anthropic/claude-sonnet-4-6",
    }.get(tier, "deepseek/deepseek-v3.2-non-thinking")


def get_available_models(provider: str = None, tier: str = None) -> list:
    """
    Zwróć listę dostępnych modeli dla danego providera i tieru.

    Args:
        provider: 'gemini', 'openrouter', lub None (aktywny)
        tier: 'free', 'cheap', 'best', lub None (wszystkie)
    """
    if provider is None:
        provider = settings.AI_PROVIDER.lower()

    if provider == "gemini":
        return [
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-pro",
            "gemini-2.5-pro",
            "gemini-3.1-pro",
        ]

    # OpenRouter — filtruj po tierze
    if tier == "free":
        return sorted(FREE_MODELS)
    elif tier == "cheap":
        return sorted(CHEAP_MODELS)
    elif tier == "best":
        return sorted(BEST_MODELS)
    else:
        return sorted(OPENROUTER_MODELS.keys())


def validate_model(model_id: str) -> bool:
    """Sprawdź czy model jest w katalogu."""
    return model_id in OPENROUTER_MODELS or model_id == "openrouter/free"


def get_model_info(model_id: str) -> dict:
    """
    Zwróć informacje o modelu z katalogu.

    Returns:
        dict z keys: context, category, tier, notes
        lub pusty dict jeśli model nieznany.
    """
    if model_id not in OPENROUTER_MODELS:
        return {}
    info = OPENROUTER_MODELS[model_id]
    parts = [p.strip() for p in info.split("|")]
    return {
        "context": parts[0] if len(parts) > 0 else "unknown",
        "category": parts[1] if len(parts) > 1 else "unknown",
        "tier": parts[2] if len(parts) > 2 else "unknown",
        "notes": parts[3] if len(parts) > 3 else "",
    }
