"""Tests for Anthropic provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from ai_code_review.models.config import AIProvider, Config
from ai_code_review.providers.anthropic import AnthropicProvider
from ai_code_review.utils.exceptions import AIProviderError


@pytest.fixture
def test_config() -> Config:
    """Test configuration for Anthropic."""
    return Config(
        gitlab_token="test_token",
        ai_provider=AIProvider.ANTHROPIC,
        ai_model="claude-sonnet-4-20250514",
        ai_api_key="test_api_key",
    )


@pytest.fixture
def dry_run_config() -> Config:
    """Dry run configuration."""
    return Config(
        gitlab_token="test_token",
        ai_provider=AIProvider.ANTHROPIC,
        ai_api_key="test_api_key",  # Need API key for validation
        dry_run=True,
    )


class TestAnthropicProvider:
    """Test Anthropic provider functionality."""

    def test_provider_initialization_success(self, test_config: Config) -> None:
        """Test Anthropic provider initialization with valid config."""
        provider = AnthropicProvider(test_config)

        assert provider.config == test_config
        assert provider.model_name == "claude-sonnet-4-20250514"
        assert provider.provider_name == "anthropic"
        assert provider._client is None

    def test_config_validation_success(self, test_config: Config) -> None:
        """Test valid configuration."""
        # Should not raise any exceptions
        provider = AnthropicProvider(test_config)
        assert provider.config.ai_api_key == "test_api_key"

    def test_config_validation_empty_api_key(self) -> None:
        """Test that Config validation catches empty API key for Anthropic."""
        # This validation now happens at Config level, not Provider level
        with pytest.raises(ValueError, match="API key is required for cloud provider"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.ANTHROPIC,
                ai_model="claude-sonnet-4-20250514",
                ai_api_key="   ",  # Whitespace only
            )

    def test_is_available_with_api_key(self, test_config: Config) -> None:
        """Test availability check with valid API key."""
        provider = AnthropicProvider(test_config)
        assert provider.is_available() is True

    def test_is_available_dry_run(self, dry_run_config: Config) -> None:
        """Test availability check in dry run mode."""
        provider = AnthropicProvider(dry_run_config)
        assert provider.is_available() is True

    @patch("ai_code_review.providers.anthropic.ChatAnthropic")
    @patch("structlog.get_logger")
    def test_create_client_success(
        self, mock_logger: MagicMock, mock_chat: MagicMock, test_config: Config
    ) -> None:
        """Test successful client creation."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        mock_client = MagicMock()
        mock_chat.return_value = mock_client

        provider = AnthropicProvider(test_config)
        client = provider._create_client()

        assert client == mock_client
        mock_chat.assert_called_once_with(
            model_name="claude-sonnet-4-20250514",
            api_key=SecretStr("test_api_key"),
            temperature=0.1,
            max_tokens_to_sample=8000,
            timeout=test_config.llm_timeout,
            max_retries=test_config.llm_max_retries,
            stop=None,
        )
        mock_logger_instance.info.assert_called_once()

    @patch("ai_code_review.providers.anthropic.ChatAnthropic")
    def test_timeout_uses_config_value(
        self, mock_chat: MagicMock, test_config: Config
    ) -> None:
        """Test that timeout uses configured llm_timeout value."""
        # Test with custom timeout
        test_config.llm_timeout = 60.0
        provider = AnthropicProvider(test_config)

        mock_chat.return_value = MagicMock()
        provider._create_client()

        # Should use the configured value (60.0)
        call_args = mock_chat.call_args[1]
        assert call_args["timeout"] == 60.0

    def test_log_rate_limit_headers_with_data(self, test_config: Config) -> None:
        """Test rate limit headers logging with actual headers."""
        provider = AnthropicProvider(test_config)

        mock_headers = {
            "anthropic-ratelimit-requests-limit": "50",
            "anthropic-ratelimit-requests-remaining": "45",
            "anthropic-ratelimit-tokens-limit": "30000",
            "anthropic-ratelimit-tokens-remaining": "25000",
            "other-header": "ignored",
        }

        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            provider._log_rate_limit_headers(mock_headers)

            # Should log rate limit info
            mock_logger.info.assert_called_once_with(
                "Anthropic rate limit status",
                **{
                    k: v
                    for k, v in mock_headers.items()
                    if k.lower().startswith("anthropic-ratelimit-")
                },
            )

    def test_log_rate_limit_headers_empty(self, test_config: Config) -> None:
        """Test rate limit headers logging with no relevant headers."""
        provider = AnthropicProvider(test_config)

        mock_headers = {
            "content-type": "application/json",
            "x-request-id": "req_123",
        }

        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            provider._log_rate_limit_headers(mock_headers)

            # Should not log anything since no rate limit headers
            mock_logger.info.assert_not_called()

    @patch("ai_code_review.providers.anthropic.ChatAnthropic")
    def test_create_client_failure(
        self, mock_chat: MagicMock, test_config: Config
    ) -> None:
        """Test client creation failure."""
        mock_chat.side_effect = Exception("API connection failed")

        provider = AnthropicProvider(test_config)
        with pytest.raises(AIProviderError, match="Failed to create Anthropic client"):
            provider._create_client()

    def test_get_adaptive_context_size_standard(self, test_config: Config) -> None:
        """Test adaptive context size for standard diff."""
        provider = AnthropicProvider(test_config)

        # Small diff (< 30K chars)
        context_size = provider.get_adaptive_context_size(20_000)
        assert context_size == 64_000

    def test_get_adaptive_context_size_medium(self, test_config: Config) -> None:
        """Test adaptive context size for medium diff."""
        provider = AnthropicProvider(test_config)

        # Medium diff (30K - 75K chars)
        context_size = provider.get_adaptive_context_size(50_000)
        assert context_size == 100_000

    def test_get_adaptive_context_size_large(self, test_config: Config) -> None:
        """Test adaptive context size for large diff."""
        provider = AnthropicProvider(test_config)

        # Large diff (75K - 150K chars)
        context_size = provider.get_adaptive_context_size(100_000)
        assert context_size == 150_000

    def test_get_adaptive_context_size_very_large(self, test_config: Config) -> None:
        """Test adaptive context size for very large diff."""
        provider = AnthropicProvider(test_config)

        # Very large diff (> 150K chars)
        context_size = provider.get_adaptive_context_size(200_000)
        assert context_size == 200_000

    def test_get_adaptive_context_size_big_diffs_flag(
        self, test_config: Config
    ) -> None:
        """Test adaptive context size with big_diffs flag."""
        provider = AnthropicProvider(test_config)
        provider.config.big_diffs = True

        # Should return max size regardless of diff size
        context_size = provider.get_adaptive_context_size(1_000)
        assert context_size == 200_000

    @pytest.mark.asyncio
    async def test_health_check_dry_run(self, dry_run_config: Config) -> None:
        """Test health check in dry run mode."""
        provider = AnthropicProvider(dry_run_config)
        result = await provider.health_check()

        expected = {
            "status": "healthy",
            "dry_run": True,
            "model": "claude-sonnet-4-20250514",
            "provider": "anthropic",
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_config: Config) -> None:
        """Test successful health check with mocked API call."""
        from unittest.mock import AsyncMock, patch

        provider = AnthropicProvider(test_config)

        # Mock the client's ainvoke method to simulate successful API call
        with patch.object(provider, "_create_client") as mock_create_client:
            mock_client = AsyncMock()
            mock_client.ainvoke.return_value = "test response"  # Mock API response
            mock_create_client.return_value = mock_client

            result = await provider.health_check()

        expected = {
            "status": "healthy",
            "api_key_configured": True,
            "api_connectivity": True,
            "model": "claude-sonnet-4-20250514",
            "provider": "anthropic",
        }
        assert result == expected

        # Verify that the API was actually called
        mock_client.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_missing_api_key(self, test_config: Config) -> None:
        """Test health check with missing API key."""
        # Test by creating a provider with valid config but then manually clearing the API key
        provider = AnthropicProvider(test_config)
        provider.config.ai_api_key = None  # Simulate missing API key at runtime

        result = await provider.health_check()

        expected = {
            "status": "unhealthy",
            "error": "Missing Anthropic API key",
            "provider": "anthropic",
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_health_check_api_failure(self, test_config: Config) -> None:
        """Test health check with API call failure."""
        from unittest.mock import AsyncMock, patch

        provider = AnthropicProvider(test_config)

        # Mock the client's ainvoke method to simulate API failure
        with patch.object(provider, "_create_client") as mock_create_client:
            mock_client = AsyncMock()
            mock_client.ainvoke.side_effect = Exception("API call failed")
            mock_create_client.return_value = mock_client

            result = await provider.health_check()

        assert result["status"] == "unhealthy"
        assert result["api_key_configured"] is True
        assert result["api_connectivity"] is False
        assert "Anthropic API test failed" in result["error"]
        assert result["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_health_check_generic_exception(self, test_config: Config) -> None:
        """Test health check with unexpected exception during processing."""
        from unittest.mock import patch

        provider = AnthropicProvider(test_config)

        # Mock _create_client to raise an unexpected exception
        with patch.object(provider, "_create_client") as mock_create_client:
            mock_create_client.side_effect = Exception("Unexpected error")

            result = await provider.health_check()

        # Should catch the exception and return unhealthy status
        assert result["status"] == "unhealthy"
        assert "Unexpected error" in result["error"]
        assert result["provider"] == "anthropic"
