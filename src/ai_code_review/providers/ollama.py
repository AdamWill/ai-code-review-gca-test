"""Ollama provider implementation using LangChain."""

from __future__ import annotations

from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

from ai_code_review.models.config import Config
from ai_code_review.providers.base import BaseAIProvider
from ai_code_review.utils.constants import (
    AUTO_BIG_DIFFS_THRESHOLD_CHARS,
    SYSTEM_PROMPT_ESTIMATED_CHARS,
)
from ai_code_review.utils.exceptions import AIProviderError


class OllamaProvider(BaseAIProvider):
    """Ollama AI provider implementation."""

    def __init__(self, config: Config) -> None:
        """Initialize Ollama provider."""
        super().__init__(config)
        self.validate_config()

    def _create_client(self) -> BaseChatModel:
        """Create ChatOllama client instance."""
        try:
            context_size = self._get_context_window_size()

            # Import logger here to avoid circular imports
            import structlog

            logger = structlog.get_logger()

            logger.info(
                "Creating Ollama client",
                model=self.model_name,
                context_window_size=context_size,
                max_tokens=self.config.max_tokens,
            )

            return ChatOllama(
                model=self.model_name,
                base_url=self.config.ollama_base_url,
                temperature=self.config.temperature,
                num_predict=self.config.max_tokens,
                num_ctx=context_size,
            )
        except Exception as e:
            raise AIProviderError(
                f"Failed to create Ollama client: {e}", "ollama"
            ) from e

    def _get_context_window_size(self) -> int:
        """Determine optimal context window size based on model capabilities."""
        # Balanced context window sizes for efficient code review
        # All Ollama models use 16K for optimal performance/memory balance
        return self._get_context_size_for_config()

    def _get_context_size_for_config(self) -> int:
        """Get context size based on configuration flags."""
        # Check if big-diffs flag is manually enabled
        if self.config.big_diffs:
            return 24576  # 24K for manually requested large diffs
        else:
            return 16384  # 16K standard - optimal balance

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
            Optimal context window size considering all content
        """
        # Calculate total content size
        total_content_chars = (
            diff_size_chars + project_context_chars + system_prompt_chars
        )

        # Manual override always takes precedence
        if self.config.big_diffs:
            return 24576  # 24K - manual big-diffs flag

        # Auto-detect large content for CI/CD scenarios (adjusted for real token ratios)
        elif (
            total_content_chars > AUTO_BIG_DIFFS_THRESHOLD_CHARS
        ):  # > 60K characters (~24K tokens with 2.5 chars/token)
            return 24576  # 24K - auto-detected large content

        else:
            return 16384  # 16K - standard size

    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        if self.config.dry_run:
            return True

        try:
            # Check if Ollama server is running
            response = httpx.get(
                f"{self.config.ollama_base_url}/api/tags",
                timeout=self.config.http_timeout,
            )
            if response.status_code != 200:
                return False

            # Check if the specific model is available
            tags = response.json()
            model_names = [model["name"] for model in tags.get("models", [])]

            # Case-insensitive exact model matching
            target_model = self.model_name.lower()
            return any(target_model == model.lower() for model in model_names)

        except Exception:
            return False

    def validate_config(self) -> None:
        """Validate Ollama-specific configuration."""
        super().validate_config()

        if not self.config.ollama_base_url:
            raise ValueError("Ollama base URL is required")

        # Validate URL format
        if not self.config.ollama_base_url.startswith(("http://", "https://")):
            raise ValueError("Ollama base URL must start with http:// or https://")

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on Ollama service."""
        if self.config.dry_run:
            return {
                "status": "healthy",
                "dry_run": True,
                "model": self.model_name,
                "provider": "ollama",
            }

        try:
            async with httpx.AsyncClient() as client:
                # Check server status
                response = await client.get(
                    f"{self.config.ollama_base_url}/api/tags",
                    timeout=self.config.http_timeout,
                )
                response.raise_for_status()

                tags = response.json()
                models = [model["name"] for model in tags.get("models", [])]

                # Case-insensitive exact model matching
                target_model = self.model_name.lower()
                model_available = any(target_model == model.lower() for model in models)

                # Find similar models for better error messages
                similar_models = []
                if not model_available:
                    model_base = (
                        target_model.split(":")[0]
                        if ":" in target_model
                        else target_model
                    )
                    similar_models = [
                        model for model in models if model_base in model.lower()
                    ]

                result = {
                    "status": "healthy" if model_available else "model_unavailable",
                    "server_reachable": True,
                    "model_available": model_available,
                    "available_models": models[:5],  # Show first 5 models
                    "requested_model": self.model_name,
                    "base_url": self.config.ollama_base_url,
                }

                # Add helpful suggestions for similar models
                if not model_available and similar_models:
                    result["similar_models"] = similar_models
                    result["suggestion"] = (
                        f"Model '{self.model_name}' not found. "
                        f"Similar available models: {', '.join(similar_models)}"
                    )
                elif not model_available:
                    result["suggestion"] = (
                        f"Model '{self.model_name}' not found. "
                        f"Available models: {', '.join(models[:3])}"
                    )

                return result

        except Exception as e:
            return {
                "status": "unhealthy",
                "server_reachable": False,
                "error": str(e),
                "base_url": self.config.ollama_base_url,
            }
