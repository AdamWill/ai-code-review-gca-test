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
        """Test config validation with missing model."""
        test_config.ai_model = None
        provider = MockAIProvider(test_config)

        with pytest.raises(ValueError, match="Model name is required for ollama"):
            provider.validate_config()

    def test_validate_config_with_empty_model(self, test_config: Config) -> None:
        """Test config validation with empty model."""
        test_config.ai_model = ""
        provider = MockAIProvider(test_config)

        with pytest.raises(ValueError, match="Model name is required for ollama"):
            provider.validate_config()

    def test_model_name_property_with_none(self, test_config: Config) -> None:
        """Test model_name property when model is None."""
        test_config.ai_model = None
        provider = MockAIProvider(test_config)

        with pytest.raises(ValueError, match="AI model is not set"):
            _ = provider.model_name
