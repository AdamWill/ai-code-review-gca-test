"""Gemini provider implementation using LangChain."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from ai_code_review.models.config import Config
from ai_code_review.providers.base import BaseAIProvider
from ai_code_review.utils.constants import SYSTEM_PROMPT_ESTIMATED_CHARS
from ai_code_review.utils.exceptions import AIProviderError


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider implementation."""

    def __init__(self, config: Config) -> None:
        """Initialize Gemini provider."""
        super().__init__(config)

    def _create_client(self) -> BaseChatModel:
        """Create ChatGoogleGenerativeAI client instance."""
        try:
            # Import logger here to avoid circular imports
            import structlog

            logger = structlog.get_logger()

            logger.info(
                "Creating Gemini client",
                model=self.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.llm_timeout,
                max_retries=self.config.llm_max_retries,
            )

            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.config.ai_api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.llm_timeout,
                max_retries=self.config.llm_max_retries,
            )
        except Exception as e:
            raise AIProviderError(
                f"Failed to create Gemini client: {e}", "gemini"
            ) from e

    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        if self.config.dry_run:
            return True

        # For cloud providers, we assume availability if we have an API key
        # Real availability check would require an actual API call
        return bool(self.config.ai_api_key)

    def get_adaptive_context_size(
        self,
        diff_size_chars: int,
        project_context_chars: int = 0,
        system_prompt_chars: int = SYSTEM_PROMPT_ESTIMATED_CHARS,
    ) -> int:
        """Get context size adaptively based on content size and config.

        Gemini 2.5 Pro has much higher limits than local models:
        - Input: ~2 million tokens
        - Output: ~8K tokens

        We can be much more generous than Ollama's 16K/24K limits.

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
            return 512_000  # 512K - manual big-diffs flag (massive context)

        # Auto-detect based on total content size (more generous than other providers)
        elif total_content_chars > 200_000:  # > 200K chars (~80K tokens)
            return 512_000  # 512K - very large content
        elif total_content_chars > 100_000:  # > 100K chars (~40K tokens)
            return 256_000  # 256K - large content
        elif total_content_chars > 30_000:  # > 30K chars (~12K tokens)
            return 128_000  # 128K - medium content
        else:
            return 64_000  # 64K - standard (still 4x larger than Ollama)

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on Gemini service."""
        if self.config.dry_run:
            return {
                "status": "healthy",
                "dry_run": True,
                "model": self.model_name,
                "provider": "gemini",
            }

        try:
            # Basic validation - API key is present and non-empty
            if not self.config.ai_api_key:
                return {
                    "status": "unhealthy",
                    "error": "Missing Google API key",
                    "provider": "gemini",
                }

            # Perform actual API health check with a minimal call
            try:
                # Create a minimal prompt to test API connectivity
                from langchain_core.messages import HumanMessage

                test_message = HumanMessage(content="test")

                # Use a very short timeout for health check
                client = self._create_client()

                # Make a minimal API call - this will validate the API key and connectivity
                # We don't need the actual response, just to verify the call works
                await client.ainvoke([test_message])

                return {
                    "status": "healthy",
                    "api_key_configured": True,
                    "api_connectivity": True,
                    "model": self.model_name,
                    "provider": "gemini",
                }

            except Exception as api_error:
                # API call failed - return specific error information
                return {
                    "status": "unhealthy",
                    "api_key_configured": True,
                    "api_connectivity": False,
                    "error": f"Gemini API test failed: {str(api_error)}",
                    "provider": "gemini",
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "provider": "gemini",
            }
