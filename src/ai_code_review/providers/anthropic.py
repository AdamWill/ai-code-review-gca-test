"""Anthropic provider implementation using LangChain."""

from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr

from ai_code_review.models.config import Config
from ai_code_review.providers.base import BaseAIProvider
from ai_code_review.utils.constants import SYSTEM_PROMPT_ESTIMATED_CHARS
from ai_code_review.utils.exceptions import AIProviderError


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude AI provider implementation."""

    def __init__(self, config: Config) -> None:
        """Initialize Anthropic provider."""
        super().__init__(config)

    def _log_rate_limit_headers(self, headers: dict[str, str]) -> None:
        """Log Anthropic rate limit headers for debugging."""
        import structlog

        logger = structlog.get_logger()

        # Extract relevant rate limit headers
        rate_limit_info = {}
        for key, value in headers.items():
            if key.lower().startswith("anthropic-ratelimit-"):
                rate_limit_info[key] = value

        if rate_limit_info:
            logger.info("Anthropic rate limit status", **rate_limit_info)

    def _create_client(self) -> BaseChatModel:
        """Create ChatAnthropic client instance."""
        try:
            # Import logger here to avoid circular imports
            import structlog

            logger = structlog.get_logger()

            logger.info(
                "Creating Anthropic client",
                model=self.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.llm_timeout,
                max_retries=self.config.llm_max_retries,
            )

            return ChatAnthropic(
                model_name=self.model_name,
                api_key=SecretStr(self.config.ai_api_key or ""),
                temperature=self.config.temperature,
                max_tokens_to_sample=self.config.max_tokens,
                timeout=self.config.llm_timeout,
                max_retries=self.config.llm_max_retries,
                stop=None,
            )
        except Exception as e:
            raise AIProviderError(
                f"Failed to create Anthropic client: {e}", "anthropic"
            ) from e

    def is_available(self) -> bool:
        """Check if Anthropic API is available."""
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

        Claude 3.5 Sonnet has excellent context handling:
        - Input: ~200K tokens (Claude 3.5 Sonnet)
        - Output: ~4K tokens

        We can be generous with context but not as much as Gemini.

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
            return 200_000  # 200K - manual big-diffs flag (max context)

        # Auto-detect based on total content size (generous but not as much as Gemini)
        elif total_content_chars > 150_000:  # > 150K chars (~60K tokens)
            return 200_000  # 200K - very large content (max context)
        elif total_content_chars > 75_000:  # > 75K chars (~30K tokens)
            return 150_000  # 150K - large content
        elif total_content_chars > 30_000:  # > 30K chars (~12K tokens)
            return 100_000  # 100K - medium content
        else:
            return 64_000  # 64K - standard (still generous)

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on Anthropic service."""
        if self.config.dry_run:
            return {
                "status": "healthy",
                "dry_run": True,
                "model": self.model_name,
                "provider": "anthropic",
            }

        try:
            # Basic validation - API key is present and non-empty
            if not self.config.ai_api_key:
                return {
                    "status": "unhealthy",
                    "error": "Missing Anthropic API key",
                    "provider": "anthropic",
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
                    "provider": "anthropic",
                }

            except Exception as api_error:
                # API call failed - return specific error information
                return {
                    "status": "unhealthy",
                    "api_key_configured": True,
                    "api_connectivity": False,
                    "error": f"Anthropic API test failed: {str(api_error)}",
                    "provider": "anthropic",
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "provider": "anthropic",
            }
