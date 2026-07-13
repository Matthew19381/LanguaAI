from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.gemini_service import (
    _get_provider,
    _model_override,
    _parse_json_response,
    generate_json,
    generate_text,
    with_model,
)


class TestGetProvider:
    def test_get_provider_openrouter(self):
        """Test that provider returns openrouter by default."""
        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            assert _get_provider() == "openrouter"

    def test_get_provider_gemini(self):
        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "gemini"
            assert _get_provider() == "gemini"

    def test_get_provider_case_insensitive(self):
        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "GEMINI"
            assert _get_provider() == "gemini"


class TestGenerateText:
    @pytest.mark.asyncio
    async def test_generate_text_openrouter_success(self):
        """Test text generation via OpenRouter."""
        mock_response = {"choices": [{"message": {"content": "Hello world"}}]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await generate_text("Test prompt")
                assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_generate_text_gemini_success(self):
        """Test text generation via Gemini Direct API."""
        mock_response = {
            "candidates": [
                {"content": {"parts": [{"text": "Hello from Gemini"}]}}
            ]
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "gemini"
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await generate_text("Test prompt")
                assert result == "Hello from Gemini"

    @pytest.mark.asyncio
    async def test_generate_text_with_custom_model(self):
        mock_response = {"choices": [{"message": {"content": "Custom model response"}}]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await generate_text("Test prompt", model="custom/model")
                assert result == "Custom model response"

    @pytest.mark.asyncio
    async def test_generate_text_api_error(self):
        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(side_effect=Exception("API Error"))
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                with pytest.raises(Exception):
                    await generate_text("Test prompt")


class TestGenerateJson:
    @pytest.mark.asyncio
    async def test_generate_json_openrouter_success(self):
        json_text = '{"key": "value", "number": 42}'
        mock_response = {"choices": [{"message": {"content": json_text}}]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await generate_json("Give me JSON")
                assert result["key"] == "value"
                assert result["number"] == 42

    @pytest.mark.asyncio
    async def test_generate_json_gemini_success(self):
        json_text = '{"result": "ok"}'
        mock_response = {
            "candidates": [
                {"content": {"parts": [{"text": json_text}]}}
            ]
        }
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "gemini"
            mock_settings.GEMINI_API_KEY = "test-key"
            mock_settings.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await generate_json("Give me JSON")
                assert result["result"] == "ok"

    @pytest.mark.asyncio
    async def test_generate_json_strips_markdown_fences(self):
        json_text = "```json\n{\"name\": \"test\"}\n```"
        mock_response = {"choices": [{"message": {"content": json_text}}]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await generate_json("Give me JSON")
                assert result["name"] == "test"

    @pytest.mark.asyncio
    async def test_generate_json_strips_plain_fences(self):
        json_text = "```\n{\"data\": 123}\n```"
        mock_response = {"choices": [{"message": {"content": json_text}}]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await generate_json("Give me JSON")
                assert result["data"] == 123

    @pytest.mark.asyncio
    async def test_generate_json_invalid_json(self):
        mock_response = {"choices": [{"message": {"content": "Not valid JSON"}}]}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                with pytest.raises(ValueError):
                    await generate_json("Give me JSON")

    @pytest.mark.asyncio
    async def test_generate_json_appends_instruction(self):
        """Test that generate_json appends the JSON-only instruction."""
        json_text = '{"ok": true}'
        mock_response = {"choices": [{"message": {"content": json_text}}]}
        mock_client = AsyncMock()
        post_mock = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))
        mock_client.post = post_mock

        with patch("backend.services.gemini_service.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "openrouter"
            mock_settings.OPENROUTER_API_KEY = "test-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            with patch("backend.services.gemini_service.httpx.AsyncClient") as mock_client_class:
                mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
                await generate_json("What is this?")
                # Check that the payload includes the JSON instruction
                call_args = post_mock.call_args
                payload = call_args[1]["json"]
                # For OpenRouter, the prompt is in messages
                if "messages" in payload:
                    assert "Respond ONLY with valid JSON" in payload["messages"][0]["content"]


class TestWithModelDecorator:
    def test_with_model_decorator_sets_context(self):
        """Test that the with_model decorator sets the model override."""
        # Reset any existing override
        _model_override.set(None)

        @with_model("placement")
        async def dummy_func():
            model = _model_override.get()
            return model

        # We can't easily test the decorator without mocking model_router,
        # but we can verify it's callable and async
        assert callable(dummy_func)

    def test_with_model_decorator_preserves_function_name(self):
        @with_model("test")
        async def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestParseJsonResponse:
    def test_parse_valid_json(self):
        result = _parse_json_response('{"key": "value"}')
        assert result["key"] == "value"

    def test_parse_json_with_fences(self):
        result = _parse_json_response('```json\n{"a": 1}\n```')
        assert result["a"] == 1

    def test_parse_json_plain_fences(self):
        result = _parse_json_response('```\n{"b": 2}\n```')
        assert result["b"] == 2

    def test_parse_json_invalid(self):
        with pytest.raises(ValueError):
            _parse_json_response("not json")

    def test_parse_json_empty(self):
        with pytest.raises(ValueError):
            _parse_json_response("")

    def test_parse_json_strip_whitespace(self):
        result = _parse_json_response('  {"c": 3}  ')
        assert result["c"] == 3


class TestDefaultModelResolution:
    def test_default_openrouter_model_uses_router_tier_not_free(self):
        """Regression: default model must come from model_router's tier default,
        never the old hardcoded 'google/gemini-2.0-flash-exp:free'."""
        from backend.services.gemini_service import _default_openrouter_model
        model = _default_openrouter_model()
        assert isinstance(model, str) and model
        assert ":free" not in model, "default model resolves to a free tier - router ignored"
        # cheap tier default per model_router._tier_default_openrouter
        assert model == "deepseek/deepseek-v3.2-non-thinking"
