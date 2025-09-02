"""Tests for Ollama provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_code_review.models.config import AIProvider, Config
from ai_code_review.providers.ollama import OllamaProvider
from ai_code_review.utils.exceptions import AIProviderError


@pytest.fixture
def test_config() -> Config:
    """Test configuration for Ollama."""
    return Config(
        gitlab_token="test_token",
        ai_provider=AIProvider.OLLAMA,
        ai_model="qwen2.5-coder:7b",
        ollama_base_url="http://localhost:11434",
    )


@pytest.fixture
def dry_run_config() -> Config:
    """Dry run configuration."""
    return Config(
        gitlab_token="test_token",
        ai_provider=AIProvider.OLLAMA,
        ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
        dry_run=True,
    )


class TestOllamaProvider:
    """Test Ollama provider functionality."""

    def test_provider_initialization(self, test_config: Config) -> None:
        """Test Ollama provider initialization."""
        provider = OllamaProvider(test_config)

        assert provider.config == test_config
        assert provider.model_name == "qwen2.5-coder:7b"
        assert provider.provider_name == "ollama"
        assert provider._client is None

    def test_config_validation_success(self, test_config: Config) -> None:
        """Test valid configuration."""
        # Should not raise any exceptions
        provider = OllamaProvider(test_config)
        assert provider.config.ollama_base_url == "http://localhost:11434"

    def test_config_validation_invalid_url(self, test_config: Config) -> None:
        """Test invalid Ollama URL."""
        test_config.ollama_base_url = "invalid_url"

        with pytest.raises(ValueError, match="Ollama base URL must start with http"):
            OllamaProvider(test_config)

    def test_client_property_creates_instance(self, test_config: Config) -> None:
        """Test client property creates ChatOllama instance."""
        provider = OllamaProvider(test_config)

        with patch("ai_code_review.providers.ollama.ChatOllama") as mock_chat:
            # Access the client property to trigger creation
            _ = provider.client

            mock_chat.assert_called_once_with(
                model="qwen2.5-coder:7b",
                base_url="http://localhost:11434",
                temperature=test_config.temperature,
                num_predict=test_config.max_tokens,
                num_ctx=16384,  # Standard 16K context window for all models
            )

    def test_is_available_dry_run(self, dry_run_config: Config) -> None:
        """Test availability check in dry run mode."""
        provider = OllamaProvider(dry_run_config)

        assert provider.is_available() is True

    def test_is_available_server_running(self, test_config: Config) -> None:
        """Test availability check with running server."""
        provider = OllamaProvider(test_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "qwen2.5-coder:7b"}, {"name": "llama2:latest"}]
        }

        with patch("httpx.get", return_value=mock_response):
            assert provider.is_available() is True

    def test_is_available_server_down(self, test_config: Config) -> None:
        """Test availability check with server down."""
        provider = OllamaProvider(test_config)

        with patch("httpx.get", side_effect=Exception("Connection failed")):
            assert provider.is_available() is False

    def test_is_available_case_insensitive(self, test_config: Config) -> None:
        """Test is_available with case differences."""
        test_config.ai_model = "qwen2.5-coder:7b"  # lowercase
        provider = OllamaProvider(test_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "qwen2.5-coder:7B"}]  # uppercase B
        }

        with patch("httpx.get", return_value=mock_response):
            assert provider.is_available() is True

    def test_is_available_wrong_model_size(self, test_config: Config) -> None:
        """Test is_available with wrong model size."""
        test_config.ai_model = "qwen2.5-coder:12B"  # 12B not available
        provider = OllamaProvider(test_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "qwen2.5-coder:7B"}]  # only 7B available
        }

        with patch("httpx.get", return_value=mock_response):
            assert provider.is_available() is False

    @pytest.mark.asyncio
    async def test_health_check_dry_run(self, dry_run_config: Config) -> None:
        """Test health check in dry run mode."""
        provider = OllamaProvider(dry_run_config)

        result = await provider.health_check()

        assert result["status"] == "healthy"
        assert result["dry_run"] is True
        assert result["provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_config: Config) -> None:
        """Test successful health check."""
        provider = OllamaProvider(test_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "qwen2.5-coder:7b"}, {"name": "llama2:latest"}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await provider.health_check()

            assert result["status"] == "healthy"
            assert result["server_reachable"] is True
            assert result["model_available"] is True
            assert "qwen2.5-coder:7b" in str(result["available_models"])

    @pytest.mark.asyncio
    async def test_health_check_server_down(self, test_config: Config) -> None:
        """Test health check with server down."""
        provider = OllamaProvider(test_config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection refused")

            result = await provider.health_check()

            assert result["status"] == "unhealthy"
            assert result["server_reachable"] is False
            assert "Connection refused" in result["error"]

    def test_client_creation_failure(self, test_config: Config) -> None:
        """Test client creation failure handling (lines 48-49)."""
        provider = OllamaProvider(test_config)

        with patch("ai_code_review.providers.ollama.ChatOllama") as mock_chat:
            mock_chat.side_effect = Exception("Failed to connect to Ollama")

            with pytest.raises(AIProviderError, match="Failed to create Ollama client"):
                _ = provider.client

    def test_get_context_size_for_config_big_diffs(self, test_config: Config) -> None:
        """Test context size configuration with big_diffs enabled (line 63)."""
        test_config.big_diffs = True
        provider = OllamaProvider(test_config)

        result = provider._get_context_size_for_config()
        assert result == 24576  # 24K for big diffs

    def test_get_adaptive_context_size_manual_big_diffs(
        self, test_config: Config
    ) -> None:
        """Test adaptive context size with manual big_diffs flag (lines 70-71)."""
        test_config.big_diffs = True
        provider = OllamaProvider(test_config)

        # Should return 24K regardless of diff size
        result = provider.get_adaptive_context_size(30000)
        assert result == 24576

    def test_get_adaptive_context_size_auto_large_diff(
        self, test_config: Config
    ) -> None:
        """Test adaptive context size with auto-detected large diff (lines 74-77)."""
        test_config.big_diffs = False
        provider = OllamaProvider(test_config)

        # Large diff should trigger 24K context
        result = provider.get_adaptive_context_size(70000)  # > 60K
        assert result == 24576

    def test_get_adaptive_context_size_standard(self, test_config: Config) -> None:
        """Test adaptive context size with standard diff (lines 79-80)."""
        test_config.big_diffs = False
        provider = OllamaProvider(test_config)

        # Standard diff should use 16K context
        result = provider.get_adaptive_context_size(30000)  # < 60K
        assert result == 16384

    def test_is_available_http_error(self, test_config: Config) -> None:
        """Test is_available with HTTP error (line 94)."""
        provider = OllamaProvider(test_config)

        # Mock httpx to raise a non-generic exception
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = ConnectionError("Network unreachable")

            result = provider.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_invalid_json_response(
        self, test_config: Config
    ) -> None:
        """Test health check with invalid JSON response (line 112)."""
        provider = OllamaProvider(test_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await provider.health_check()

            assert result["status"] == "unhealthy"
            assert result["server_reachable"] is False  # Exception makes it unreachable
            assert "Invalid JSON" in result["error"]
