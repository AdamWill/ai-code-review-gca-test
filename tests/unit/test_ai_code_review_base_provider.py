"""Tests for base AI provider."""

from __future__ import annotations

import pytest

from ai_code_review.models.config import AIProvider, Config
from ai_code_review.providers.base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Mock implementation of BaseAIProvider for testing."""

    def _create_client(self):
        """Mock client creation."""
        return "mock_client"

    def is_available(self) -> bool:
        """Mock availability check."""
        return True

    def get_adaptive_context_size(self, diff_char_count: int) -> int:
        """Mock context size calculation."""
        return 4000

    async def health_check(self) -> dict:
        """Mock health check."""
        return {"status": "healthy"}


class TestBaseAIProvider:
    """Test BaseAIProvider abstract class."""

    @pytest.fixture
    def test_config(self) -> Config:
        """Test configuration."""
        return Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="test-model",
        )

    def test_provider_initialization(self, test_config: Config) -> None:
        """Test provider initialization."""
        provider = MockAIProvider(test_config)

        assert provider.config == test_config
        assert provider._client is None

    def test_client_property_creates_client(self, test_config: Config) -> None:
        """Test that client property creates client on first access."""
        provider = MockAIProvider(test_config)

        # First access should create client
        client = provider.client
        assert client == "mock_client"
        assert provider._client == "mock_client"

        # Second access should return same client
        client2 = provider.client
        assert client2 == "mock_client"

    def test_model_name_property(self, test_config: Config) -> None:
        """Test model_name property."""
        provider = MockAIProvider(test_config)

        assert provider.model_name == "test-model"

    def test_provider_name_property(self, test_config: Config) -> None:
        """Test provider_name property."""
        provider = MockAIProvider(test_config)

        assert provider.provider_name == "ollama"

    def test_validate_config_with_missing_model(self, test_config: Config) -> None:
        """Test config validation with missing model uses default."""
        test_config.ai_model = None
        provider = MockAIProvider(test_config)

        # With new behavior, get_ai_model() returns default model for provider
        # So validation should pass and return default model
        provider.validate_config()
        assert provider.model_name == "qwen2.5-coder:7b"  # Default for Ollama

    def test_validate_config_with_empty_model(self, test_config: Config) -> None:
        """Test config validation with empty model uses default.

        Note: Empty strings are normalized to None by the validator,
        then get_ai_model() returns the provider's default model.
        """
        test_config.ai_model = ""
        provider = MockAIProvider(test_config)

        # Empty string is normalized to None, then uses default
        provider.validate_config()
        assert provider.model_name == "qwen2.5-coder:7b"  # Default for Ollama

    def test_model_name_property_with_none(self, test_config: Config) -> None:
        """Test model_name property when model is None returns default."""
        test_config.ai_model = None
        provider = MockAIProvider(test_config)

        # With new behavior, get_ai_model() returns default model for provider
        assert provider.model_name == "qwen2.5-coder:7b"  # Default for Ollama

    def test_empty_model_normalized_during_construction(self) -> None:
        """Test that empty string is normalized to None during Config construction."""
        # Create config with empty string for ai_model
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="",  # Empty string should be normalized to None
        )

        # Empty string should be normalized to None by validator
        assert config.ai_model is None
        # get_ai_model() should return provider's default
        assert config.get_ai_model() == "qwen2.5-coder:7b"
