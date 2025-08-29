"""Configuration models for AI Code Review tool."""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class AIProvider(str, Enum):
    """Supported AI providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Config(BaseSettings):
    """Main configuration for AI Code Review tool."""

    # GitLab configuration
    gitlab_token: str = Field(description="GitLab Personal Access Token")
    gitlab_url: str = Field(
        default="https://gitlab.com", description="GitLab instance URL"
    )

    # AI provider configuration
    ai_provider: AIProvider = Field(
        default=AIProvider.OLLAMA, description="AI provider to use"
    )
    ai_model: str = Field(default="qwen2.5-coder:7b", description="AI model name")
    ai_api_key: str | None = Field(
        default=None, description="API key for cloud AI providers"
    )

    # Ollama specific
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL for local development",
    )

    # Content processing
    max_chars: int = Field(
        default=100_000, description="Maximum characters to process from diff"
    )
    max_files: int = Field(
        default=100, description="Maximum number of files to process"
    )

    # Optional features
    language_hint: str | None = Field(
        default=None, description="Programming language hint"
    )

    # Execution options
    dry_run: bool = Field(default=False, description="Dry run mode (no API calls)")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("ai_api_key")
    @classmethod
    def validate_api_key(cls, v: str | None) -> str | None:
        """Validate that API key is provided for cloud providers."""
        # For MVP, we'll keep this simple and validate in the main app logic
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",
    }
