"""Configuration models for AI Code Review tool."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings


def get_default_exclude_patterns() -> list[str]:
    """Get the default list of file patterns to exclude from AI review."""
    return [
        "*.lock",  # All lockfiles (uv.lock, pdm.lock, etc.)
        "package-lock.json",  # npm lockfile
        "yarn.lock",  # Yarn lockfile
        "Pipfile.lock",  # Pipenv lockfile
        "poetry.lock",  # Poetry lockfile
        "pnpm-lock.yaml",  # PNPM lockfile
        "*.min.js",  # Minified JS files
        "*.min.css",  # Minified CSS files
        "*.map",  # Source map files
        "node_modules/**",  # Node modules (top level)
        "**/node_modules/**",  # Node modules (nested)
        "__pycache__/**",  # Python cache (top level)
        "**/__pycache__/**",  # Python cache (nested)
        "dist/**",  # Build distributions (top level)
        "**/dist/**",  # Build distributions (nested)
        "build/**",  # Build directories (top level)
        "**/build/**",  # Build directories (nested)
        "*.egg-info/**",  # Python egg info (top level)
        "**/*.egg-info/**",  # Python egg info (nested)
    ]


def get_default_model_for_provider(provider: AIProvider) -> str:
    """Get default model name for each AI provider."""
    defaults = {
        AIProvider.OLLAMA: "qwen2.5-coder:7b",
        AIProvider.GEMINI: "gemini-2.5-pro",
        AIProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    }
    return defaults.get(provider, "gemini-2.5-pro")  # Fallback to gemini default


class AIProvider(str, Enum):
    """Supported AI providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# Cloud AI providers that require API keys
CLOUD_PROVIDERS = {
    AIProvider.GEMINI,
    AIProvider.OPENAI,
    AIProvider.ANTHROPIC,
}


class Config(BaseSettings):
    """Main configuration for AI Code Review tool."""

    # GitLab configuration
    gitlab_token: str = Field(description="GitLab Personal Access Token")
    gitlab_url: str = Field(
        default="https://gitlab.com", description="GitLab instance URL"
    )

    # AI provider configuration
    ai_provider: AIProvider = Field(
        default=AIProvider.GEMINI, description="AI provider to use"
    )
    ai_model: str | None = Field(default=None, description="AI model name")
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
        default=8000,
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

    # File filtering
    exclude_patterns: list[str] = Field(
        default_factory=get_default_exclude_patterns,
        description="Glob patterns for files to exclude from AI review",
    )

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
    def validate_ai_model(cls, v: str | None) -> str | None:
        """Validate AI model name format."""
        if v is None:
            return None  # Will be set by model validator

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

    @field_validator("gitlab_token")
    @classmethod
    def validate_gitlab_token(cls, v: str) -> str:
        """Validate GitLab token format and provide helpful error message."""
        if not v or not v.strip():
            raise ValueError(
                "GitLab Personal Access Token is required. "
                "Get one at: https://gitlab.com/-/profile/personal_access_tokens "
                "with scopes: api, read_user, read_repository. "
                "Set it as GITLAB_TOKEN environment variable or in .env file."
            )

        v = v.strip()

        # Allow test tokens (common patterns used in testing)
        test_patterns = ("test", "mock", "fake", "dummy", "example")
        if any(pattern in v.lower() for pattern in test_patterns):
            return v

        # Validate format only for tokens that appear to be real GitLab tokens
        # (longer than 20 chars and don't contain obvious test words)
        if len(v) > 20 and not any(pattern in v.lower() for pattern in test_patterns):
            if not v.startswith(("glpat-", "gldt-", "glrt-", "gloas-", "glcpat-")):
                raise ValueError(
                    f"GitLab token format appears invalid: '{v[:12]}...'. "
                    "GitLab tokens typically start with: glpat- (personal), "
                    "gldt- (deploy), glrt- (runner), gloas- (OAuth app), "
                    "or glcpat- (project access). "
                    "Get a valid token at: https://gitlab.com/-/profile/personal_access_tokens"
                )

        return v

    @field_validator("ai_api_key")
    @classmethod
    def validate_api_key(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate that API key is provided for cloud providers."""
        # Get the provider from validation context
        if info.data and "ai_provider" in info.data:
            provider = info.data["ai_provider"]

            if provider in CLOUD_PROVIDERS:
                if not v or (isinstance(v, str) and not v.strip()):
                    provider_urls = {
                        AIProvider.GEMINI: "https://makersuite.google.com/app/apikey",
                        AIProvider.OPENAI: "https://platform.openai.com/api-keys",
                        AIProvider.ANTHROPIC: "https://console.anthropic.com/",
                    }
                    url = provider_urls.get(provider, "provider website")
                    raise ValueError(
                        f"API key is required for cloud provider '{provider.value}'. "
                        f"Get one at: {url} "
                        f"Set it as AI_API_KEY environment variable or in .env file."
                    )

        return v

    @model_validator(mode="before")
    @classmethod
    def validate_required_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate required fields and set default models per provider."""
        if isinstance(data, dict):
            # Check if gitlab_token is missing or empty
            token = data.get("gitlab_token")
            if not token or (isinstance(token, str) and not token.strip()):
                raise ValueError(
                    "GitLab Personal Access Token is required. "
                    "Get one at: https://gitlab.com/-/profile/personal_access_tokens "
                    "with scopes: api, read_user, read_repository. "
                    "Set it as GITLAB_TOKEN environment variable or in .env file."
                )

                # Set default model based on provider if model not explicitly set
            provider_str = data.get("ai_provider")
            model = data.get("ai_model")

            # Only set default if model is None (not provided at all)
            if provider_str and model is None:
                if isinstance(provider_str, str):
                    try:
                        provider = AIProvider(provider_str)
                        data["ai_model"] = get_default_model_for_provider(provider)
                    except ValueError:
                        # Invalid provider, let other validators handle it
                        pass

        return data

    @model_validator(mode="after")
    @classmethod
    def validate_model_provider_compatibility(cls, config: Any) -> Any:
        """Validate that the AI model is compatible with the selected provider."""
        provider = config.ai_provider
        model = config.ai_model

        # Ensure ai_model is set (should have been set by validate_required_fields)
        if model is None:
            raise ValueError(
                f"AI model is required but was not set for provider {provider.value}"
            )

        # Check for obvious mismatches
        if provider == AIProvider.OLLAMA:
            # Ollama shouldn't use cloud provider model names
            if model.startswith(("gemini-", "gpt-", "claude-")):
                suggested_model = "qwen2.5-coder:7b"
                raise ValueError(
                    f"AI model '{model}' appears to be for a cloud provider, "
                    f"but you selected Ollama provider. "
                    f"For Ollama, try a model like '{suggested_model}'. "
                    f"Or change ai_provider to match your model choice."
                )
        elif provider == AIProvider.GEMINI:
            # Gemini should use gemini models
            if not model.startswith("gemini-") and model not in [
                "gemini-pro",
                "gemini-pro-vision",
            ]:
                suggested_model = "gemini-2.5-pro"
                raise ValueError(
                    f"AI model '{model}' may not be compatible with Gemini provider. "
                    f"For Gemini, try a model like '{suggested_model}'. "
                    f"Or change ai_provider to match your model choice."
                )

        return config

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
