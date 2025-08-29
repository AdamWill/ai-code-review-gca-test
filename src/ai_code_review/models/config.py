"""Configuration models for AI Code Review tool."""

from __future__ import annotations

import re
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
    http_timeout: float = Field(
        default=5.0,
        description="HTTP request timeout in seconds for API calls",
        gt=0.0,
    )

    # AI model parameters
    temperature: float = Field(
        default=0.1,
        description="Temperature for AI responses (0.0-2.0, lower = more deterministic)",
        ge=0.0,
        le=2.0,
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for AI response generation",
        gt=0,
    )

    # Content processing
    max_chars: int = Field(
        default=100_000, description="Maximum characters to process from diff"
    )
    max_files: int = Field(
        default=100, description="Maximum number of files to process"
    )

    # GitLab CI/CD automatic variables (optional)
    ci_project_path: str | None = Field(
        default=None, description="GitLab CI project path (automatically set in CI/CD)"
    )
    ci_merge_request_iid: int | None = Field(
        default=None,
        description="GitLab CI merge request IID (automatically set in CI/CD)",
    )
    ci_server_url: str | None = Field(
        default=None, description="GitLab CI server URL (automatically set in CI/CD)"
    )

    # Optional features
    language_hint: str | None = Field(
        default=None, description="Programming language hint"
    )

    # Execution options
    dry_run: bool = Field(default=False, description="Dry run mode (no API calls)")
    big_diffs: bool = Field(
        default=False,
        description="Force larger context window (24K) - auto-activated for diffs >60K chars",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("gitlab_url", "ollama_base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v:
            raise ValueError("URL cannot be empty")

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v):
            raise ValueError(f"Invalid URL format: {v}")

        return v.rstrip("/")  # Remove trailing slash for consistency

    @field_validator("ai_model")
    @classmethod
    def validate_ai_model(cls, v: str) -> str:
        """Validate AI model name format."""
        if not v or not v.strip():
            raise ValueError("AI model name cannot be empty")

        # Basic validation: no special characters that could cause issues
        if any(char in v for char in ["\n", "\r", "\t", "\0"]):
            raise ValueError("AI model name contains invalid characters")

        return v.strip()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

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

    def get_effective_project_id(self) -> str | None:
        """Get effective project ID from CI environment or explicit config."""
        return self.ci_project_path

    def get_effective_mr_iid(self) -> int | None:
        """Get effective MR IID from CI environment or explicit config."""
        return self.ci_merge_request_iid

    def get_effective_gitlab_url(self) -> str:
        """Get effective GitLab URL prioritizing CI environment."""
        return self.ci_server_url or self.gitlab_url

    def is_ci_mode(self) -> bool:
        """Check if running in GitLab CI/CD environment."""
        return bool(self.ci_project_path and self.ci_merge_request_iid)
