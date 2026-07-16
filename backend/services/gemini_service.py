import contextvars
import functools
import json
import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# OpenRouter settings
_OPENROUTER_URL = f"{settings.OPENROUTER_BASE_URL}/chat/completions"
# Default model is resolved from model_router's tier default (not hardcoded :free),
# so the curated catalog in model_router.py is always respected.
def _default_openrouter_model() -> str:
    from backend.services.model_router import _tier_default_openrouter
    tier = getattr(settings, "AI_MODEL_TIER", "cheap") or "cheap"
    return _tier_default_openrouter(tier)

# Gemini Direct API settings
_GEMINI_BASE_URL = settings.GEMINI_BASE_URL
_GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"


# ContextVar for per-request model override (async-safe)
_model_override: contextvars.ContextVar[str] = contextvars.ContextVar('model_override', default=None)


def set_model_override(model: str):
    """Set the model for the current async context."""
    return _model_override.set(model)


def reset_model_override(token):
    """Reset the model to previous value."""
    _model_override.reset(token)


def with_model(task: str):
    """
    Decorator for AI-generating functions.
    Sets the appropriate model for the duration of the function call.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, model=None, **kwargs):
            if model is None:
                from backend.services.model_router import get_model_for_task
                model = get_model_for_task(task)
            token = set_model_override(model)
            try:
                return await func(*args, **kwargs)
            finally:
                reset_model_override(token)
        return wrapper
    return decorator


def _get_provider() -> str:
    """Return the current AI provider: 'gemini' or 'openrouter'."""
    return settings.AI_PROVIDER.lower()


def _get_gemini_url(model: str) -> str:
    """Build URL for Gemini Direct API."""
    return f"{_GEMINI_BASE_URL}/models/{model}:generateContent"


def _get_openrouter_url() -> str:
    """Return URL for OpenRouter API."""
    return _OPENROUTER_URL


def _build_gemini_payload(prompt: str) -> dict:
    """Build request payload for Gemini Direct API."""
    return {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
        }
    }


def _build_openrouter_payload(prompt: str, model: str) -> dict:
    """Build request payload for OpenRouter API."""
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }


def _get_gemini_headers() -> dict:
    """Headers for Gemini Direct API (uses URL param for key)."""
    return {
        "Content-Type": "application/json",
    }


def _get_openrouter_headers() -> dict:
    """Headers for OpenRouter API."""
    return {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.FRONTEND_URL,
        "X-Title": "LinguaAI",
    }


async def _call_gemini_api(url: str, payload: dict, headers: dict, timeout: float = 60.0) -> str:
    """Call Gemini Direct API and return response text."""
    params = {"key": settings.GEMINI_API_KEY}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, json=payload, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            # Extract text from Gemini response format
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise


async def _call_openrouter_api(url: str, payload: dict, headers: dict, timeout: float = 60.0) -> str:
    """Call OpenRouter API and return response text."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            raise


async def generate_text(prompt: str, model: str = None) -> str:
    """Generate text using configured AI provider."""
    provider = _get_provider()

    if provider == "gemini":
        return await _generate_text_gemini(prompt, model)
    else:
        return await _generate_text_openrouter(prompt, model)


async def _generate_text_gemini(prompt: str, model: str = None) -> str:
    """Generate text using Gemini Direct API."""
    if model is None:
        model = _model_override.get() or _GEMINI_DEFAULT_MODEL
    url = _get_gemini_url(model)
    headers = _get_gemini_headers()
    payload = _build_gemini_payload(prompt)
    return await _call_gemini_api(url, payload, headers, timeout=60.0)


async def _generate_text_openrouter(prompt: str, model: str = None) -> str:
    """Generate text using OpenRouter API."""
    if model is None:
        model = _model_override.get() or _default_openrouter_model()
    url = _get_openrouter_url()
    headers = _get_openrouter_headers()
    payload = _build_openrouter_payload(prompt, model)
    return await _call_openrouter_api(url, payload, headers, timeout=60.0)


async def generate_json(prompt: str, model: str = None) -> dict:
    """Generate JSON using configured AI provider."""
    provider = _get_provider()

    if provider == "gemini":
        return await _generate_json_gemini(prompt, model)
    else:
        return await _generate_json_openrouter(prompt, model)


async def _generate_json_gemini(prompt: str, model: str = None) -> dict:
    """Generate JSON using Gemini Direct API."""
    if model is None:
        model = _model_override.get() or _GEMINI_DEFAULT_MODEL
    full_prompt = prompt + "\n\nRespond ONLY with valid JSON, no markdown, no code blocks."
    url = _get_gemini_url(model)
    headers = _get_gemini_headers()
    payload = _build_gemini_payload(full_prompt)
    text = await _call_gemini_api(url, payload, headers, timeout=120.0)
    return _parse_json_response(text)


async def _generate_json_openrouter(prompt: str, model: str = None) -> dict:
    """Generate JSON using OpenRouter API."""
    if model is None:
        model = _model_override.get() or _default_openrouter_model()
    full_prompt = prompt + "\n\nRespond ONLY with valid JSON, no markdown, no code blocks."
    url = _get_openrouter_url()
    headers = _get_openrouter_headers()
    payload = _build_openrouter_payload(full_prompt, model)
    text = await _call_openrouter_api(url, payload, headers, timeout=120.0)
    return _parse_json_response(text)


def _parse_json_response(text: str, fallback: dict | None = None) -> dict:
    """Parse JSON from AI response, stripping markdown fences if present.

    On parse failure: returns ``fallback`` if provided (graceful degradation
    per CLAUDE.md), otherwise raises ValueError so the caller can decide.
    """
    text = text.strip()

    # Strip markdown fences if model adds them
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lower().startswith("json"):
                text = text[4:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if fallback is not None:
            logger.error(f"JSON decode error (using fallback): {e}. Raw: {text[:200]}")
            return fallback
        logger.error(f"JSON decode error: {e}. Raw response: {text[:500]}")
        raise ValueError(f"Invalid JSON response from AI: {e}")
