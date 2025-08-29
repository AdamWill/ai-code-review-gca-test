"""Base AI provider abstraction using LangChain."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel

from ai_code_review.models.config import Config


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: Config) -> None:
        """Initialize AI provider."""
        self.config = config
        self._client: BaseChatModel | None = None

    @property
    def client(self) -> BaseChatModel:
        """Get or create AI client instance."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self.config.ai_model

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return self.config.ai_provider.value

    @abstractmethod
    def _create_client(self) -> BaseChatModel:
        """Create the LangChain client instance."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    def validate_config(self) -> None:
        """Validate provider-specific configuration."""
        # Base validation - subclasses can override
        if not self.config.ai_model:
            raise ValueError(f"Model name is required for {self.provider_name}")
