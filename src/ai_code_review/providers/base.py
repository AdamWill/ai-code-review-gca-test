"""Base AI provider abstraction using LangChain."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel

from ai_code_review.models.config import Config
from ai_code_review.utils.constants import SYSTEM_PROMPT_ESTIMATED_CHARS


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
        return self.config.get_ai_model()

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

    @abstractmethod
    def get_adaptive_context_size(
        self,
        diff_size_chars: int,
        project_context_chars: int = 0,
        system_prompt_chars: int = SYSTEM_PROMPT_ESTIMATED_CHARS,
    ) -> int:
        """Get context size adaptively based on content size and config.

        Args:
            diff_size_chars: Size of the diff content in characters
            project_context_chars: Size of project context content in characters
            system_prompt_chars: Estimated size of system prompt in characters

        Returns:
            Optimal context window size for this provider
        """
        pass

    def validate_config(self) -> None:
        """Validate provider-specific configuration."""
        # Base validation - subclasses can override
        model = self.config.get_ai_model()
        if not model:
            raise ValueError(f"Model name is required for {self.provider_name}")
