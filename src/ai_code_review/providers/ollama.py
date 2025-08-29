"""Ollama provider implementation using LangChain."""

from __future__ import annotations

from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

from ai_code_review.models.config import Config
from ai_code_review.providers.base import BaseAIProvider
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
            return ChatOllama(
                model=self.config.ai_model,
                base_url=self.config.ollama_base_url,
                temperature=self.config.temperature,
                num_predict=self.config.max_tokens,
            )
        except Exception as e:
            raise AIProviderError(
                f"Failed to create Ollama client: {e}", "ollama"
            ) from e

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

            # Check for exact match or partial match (e.g., "qwen2.5-coder:7b" in ["qwen2.5-coder:latest"])
            return any(
                self.config.ai_model in model_name or model_name in self.config.ai_model
                for model_name in model_names
            )

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
                "model": self.config.ai_model,
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
                model_available = any(
                    self.config.ai_model in model or model in self.config.ai_model
                    for model in models
                )

                return {
                    "status": "healthy" if model_available else "model_unavailable",
                    "server_reachable": True,
                    "model_available": model_available,
                    "available_models": models[:5],  # Show first 5 models
                    "requested_model": self.config.ai_model,
                    "base_url": self.config.ollama_base_url,
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "server_reachable": False,
                "error": str(e),
                "base_url": self.config.ollama_base_url,
            }
