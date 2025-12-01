"""Tests for Gemini provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_code_review.models.config import AIProvider, Config
from ai_code_review.providers.gemini import GeminiProvider
from ai_code_review.utils.exceptions import AIProviderError


@pytest.fixture
def test_config() -> Config:
    """Test configuration for Gemini."""
    return Config(
        gitlab_token="test_token",
        ai_provider=AIProvider.GEMINI,
        ai_model="gemini-2.5-pro",
        ai_api_key="test_api_key",
    )


@pytest.fixture
def dry_run_config() -> Config:
    """Dry run configuration."""
    return Config(
        gitlab_token="test_token",
        ai_provider=AIProvider.GEMINI,
        ai_api_key="test_api_key",  # Need API key for validation
        dry_run=True,
    )


class TestGeminiProvider:
    """Test Gemini provider functionality."""

    def test_provider_initialization_success(self, test_config: Config) -> None:
        """Test Gemini provider initialization with valid config."""
        provider = GeminiProvider(test_config)

        assert provider.config == test_config
        assert provider.model_name == "gemini-2.5-pro"
        assert provider.provider_name == "gemini"
        assert provider._client is None

    def test_config_validation_success(self, test_config: Config) -> None:
        """Test valid configuration."""
        # Should not raise any exceptions
        provider = GeminiProvider(test_config)
        assert provider.config.ai_api_key == "test_api_key"

    def test_config_validation_empty_api_key(self) -> None:
        """Test that Config validation catches empty API key for Gemini."""
        # This validation now happens at Config level, not Provider level
        with pytest.raises(ValueError, match="API key is required for cloud provider"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.GEMINI,
                ai_model="gemini-2.5-pro",
                ai_api_key="   ",  # Whitespace only
            )

    def test_is_available_with_api_key(self, test_config: Config) -> None:
        """Test availability check with valid API key."""
        provider = GeminiProvider(test_config)
        assert provider.is_available() is True

    def test_is_available_dry_run(self, dry_run_config: Config) -> None:
        """Test availability check in dry run mode."""
        provider = GeminiProvider(dry_run_config)
        assert provider.is_available() is True

    @patch("ai_code_review.providers.gemini.ChatGoogleGenerativeAI")
    @patch("structlog.get_logger")
    def test_create_client_success(
        self, mock_logger: MagicMock, mock_chat: MagicMock, test_config: Config
    ) -> None:
        """Test successful client creation."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_client = MagicMock()
        mock_chat.return_value = mock_client

        provider = GeminiProvider(test_config)
        client = provider._create_client()

        assert client == mock_client
        mock_chat.assert_called_once_with(
            model="gemini-2.5-pro",
            google_api_key="test_api_key",
            temperature=0.1,
            max_tokens=8000,
            timeout=test_config.llm_timeout,
            max_retries=test_config.llm_max_retries,
        )
        mock_logger_instance.info.assert_called_once()

    @patch("ai_code_review.providers.gemini.ChatGoogleGenerativeAI")
    def test_create_client_failure(
        self, mock_chat: MagicMock, test_config: Config
    ) -> None:
        """Test client creation failure."""
        mock_chat.side_effect = Exception("API connection failed")

        provider = GeminiProvider(test_config)
        with pytest.raises(AIProviderError, match="Failed to create Gemini client"):
            provider._create_client()

    def test_get_adaptive_context_size_standard(self, test_config: Config) -> None:
        """Test adaptive context size for standard diff."""
        provider = GeminiProvider(test_config)

        # Small diff (< 30K chars)
        context_size = provider.get_adaptive_context_size(20_000)
        assert context_size == 64_000

    def test_get_adaptive_context_size_medium(self, test_config: Config) -> None:
        """Test adaptive context size for medium diff."""
        provider = GeminiProvider(test_config)

        # Medium diff (30K - 100K chars)
        context_size = provider.get_adaptive_context_size(50_000)
        assert context_size == 128_000

    def test_get_adaptive_context_size_large(self, test_config: Config) -> None:
        """Test adaptive context size for large diff."""
        provider = GeminiProvider(test_config)

        # Large diff (100K - 200K chars)
        context_size = provider.get_adaptive_context_size(150_000)
        assert context_size == 256_000

    def test_get_adaptive_context_size_very_large(self, test_config: Config) -> None:
        """Test adaptive context size for very large diff."""
        provider = GeminiProvider(test_config)

        # Very large diff (> 200K chars)
        context_size = provider.get_adaptive_context_size(300_000)
        assert context_size == 512_000

    def test_get_adaptive_context_size_big_diffs_flag(
        self, test_config: Config
    ) -> None:
        """Test adaptive context size with big_diffs flag."""
        provider = GeminiProvider(test_config)
        provider.config.big_diffs = True

        # Should return max size regardless of diff size
        context_size = provider.get_adaptive_context_size(1_000)
        assert context_size == 512_000

    @pytest.mark.asyncio
    async def test_health_check_dry_run(self, dry_run_config: Config) -> None:
        """Test health check in dry run mode."""
        from ai_code_review.models.config import _DEFAULT_MODELS, AIProvider

        provider = GeminiProvider(dry_run_config)
        result = await provider.health_check()

        expected = {
            "status": "healthy",
            "dry_run": True,
            "model": _DEFAULT_MODELS[AIProvider.GEMINI],
            "provider": "gemini",
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_config: Config) -> None:
        """Test successful health check with mocked API call."""
        from unittest.mock import AsyncMock, patch

        provider = GeminiProvider(test_config)

        # Mock the client's ainvoke method to simulate successful API call
        with patch.object(provider, "_create_client") as mock_create_client:
            mock_client = AsyncMock()
            mock_client.ainvoke.return_value = "test response"  # Mock API response
            mock_create_client.return_value = mock_client

            result = await provider.health_check()

        expected = {
            "status": "healthy",
            "api_key_configured": True,
            "api_connectivity": True,  # New field from improved health check
            "model": "gemini-2.5-pro",
            "provider": "gemini",
        }
        assert result == expected

        # Verify that the API was actually called
        mock_client.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_missing_api_key(self) -> None:
        """Test health check when API key is missing (covers lines 112-116)."""
        config = Config(
            gitlab_token="test-token",
            ai_provider=AIProvider.GEMINI,
            ai_model="gemini-2.5-pro",
            ai_api_key="fake-key",  # Will be set to None below
            dry_run=False,  # Need dry_run=False to test API key validation
        )
        # Explicitly set ai_api_key to None to trigger the error path
        config.ai_api_key = None

        provider = GeminiProvider(config)
        result = await provider.health_check()

        expected = {
            "status": "unhealthy",
            "error": "Missing Google API key",
            "provider": "gemini",
        }
        assert result == expected
