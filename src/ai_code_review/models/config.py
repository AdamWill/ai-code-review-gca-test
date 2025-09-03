"""Configuration models for AI Code Review tool."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import (
    AliasChoices,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings


# PlatformProvider moved here to avoid circular imports
class PlatformProvider(str, Enum):
    """Supported code hosting platforms."""

    GITLAB = "gitlab"
    GITHUB = "github"
    LOCAL = "local"


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
    """Get default model name for each AI provider.

    Raises:
        ValueError: If no default model is defined for the provider.
    """
    defaults = {
        AIProvider.OLLAMA: "qwen2.5-coder:7b",
        AIProvider.GEMINI: "gemini-2.5-pro",
        AIProvider.ANTHROPIC: "claude-sonnet-4-20250514",
        AIProvider.OPENAI: "gpt-5-mini",  # Default for future OpenAI implementation
    }

    if provider not in defaults:
        raise ValueError(
            f"No default model defined for provider '{provider.value}'. "
            f"Please add a default model in get_default_model_for_provider() "
            f"for provider {provider}."
        )

    return defaults[provider]


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

    # Platform configuration
    platform_provider: PlatformProvider = Field(
        default=PlatformProvider.GITLAB, description="Code hosting platform to use"
    )

    # GitLab configuration
    gitlab_token: str | None = Field(
        default=None, description="GitLab Personal Access Token"
    )
    gitlab_url: str = Field(
        default="https://gitlab.com", description="GitLab instance URL"
    )

    # GitHub configuration
    github_token: str | None = Field(
        default=None, description="GitHub Personal Access Token"
    )
    github_url: str = Field(
        default="https://api.github.com", description="GitHub API URL"
    )

    # SSL configuration
    ssl_verify: bool = Field(
        default=True,
        description="Verify SSL certificates (disable only for development)",
    )
    ssl_cert_path: str | None = Field(
        default=None,
        description="Path to SSL certificate file for custom CA or self-signed certificates",
    )
    ssl_cert_url: str | None = Field(
        default=None,
        description="URL to download SSL certificate automatically (alternative to ssl_cert_path)",
    )
    ssl_cert_cache_dir: str = Field(
        default=".ssl_cache",
        description="Directory to cache downloaded SSL certificates",
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

    # CI/CD automatic variables (platform-agnostic)
    repository_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_REPOSITORY", "CI_PROJECT_PATH"),
        description="Repository path (CI_PROJECT_PATH for GitLab, GITHUB_REPOSITORY for GitHub)",
    )
    pull_request_number: int | None = Field(
        default=None,
        validation_alias=AliasChoices("CI_MERGE_REQUEST_IID"),
        description="Pull/merge request number (CI_MERGE_REQUEST_IID for GitLab, derived from GitHub event)",
    )
    server_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_SERVER_URL", "CI_SERVER_URL"),
        description="Platform server URL (CI_SERVER_URL for GitLab, GITHUB_SERVER_URL for GitHub)",
    )

    # Legacy GitLab CI/CD variables (for backward compatibility)
    ci_project_path: str | None = Field(
        default=None,
        description="GitLab CI project path (deprecated, use repository_path)",
    )
    ci_merge_request_iid: int | None = Field(
        default=None,
        description="GitLab CI merge request IID (deprecated, use pull_request_number)",
    )
    ci_server_url: str | None = Field(
        default=None, description="GitLab CI server URL (deprecated, use server_url)"
    )

    # Optional features
    language_hint: str | None = Field(
        default=None, description="Programming language hint"
    )
    enable_project_context: bool = Field(
        default=True,
        description="Enable loading project context from .ai_review/project.md file",
    )
    project_context_file: str = Field(
        default=".ai_review/project.md",
        description="Path to project context file (relative to repository root)",
    )
    include_mr_summary: bool = Field(
        default=True,
        description="Include MR Summary section in reviews (disable for shorter, code-focused reviews)",
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

    @field_validator("gitlab_url", "github_url", "ollama_base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v:
            raise ValueError("URL cannot be empty")

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v):
            raise ValueError(f"Invalid URL format: {v}")

        return v.rstrip("/")  # Remove trailing slash for consistency

    @field_validator("ssl_cert_path")
    @classmethod
    def validate_ssl_cert_path(cls, v: str | None) -> str | None:
        """Validate SSL certificate file path."""
        if v is None:
            return None

        if not v.strip():
            raise ValueError("SSL certificate path cannot be empty")

        import os

        if not os.path.isfile(v):
            raise ValueError(f"SSL certificate file not found: {v}")

        if not os.access(v, os.R_OK):
            raise ValueError(f"SSL certificate file is not readable: {v}")

        return v

    @field_validator("ssl_cert_url")
    @classmethod
    def validate_ssl_cert_url(cls, v: str | None) -> str | None:
        """Validate SSL certificate URL format."""
        if v is None:
            return None

        if not v.strip():
            raise ValueError("SSL certificate URL cannot be empty")

        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, v):
            raise ValueError(f"Invalid SSL certificate URL format: {v}")

        return v.rstrip("/")

    @field_validator("ssl_cert_cache_dir")
    @classmethod
    def validate_ssl_cert_cache_dir(cls, v: str) -> str:
        """Validate SSL certificate cache directory."""
        if not v.strip():
            raise ValueError("SSL certificate cache directory cannot be empty")
        return v.strip()

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
    def validate_gitlab_token(cls, v: str | None) -> str | None:
        """Validate GitLab token format and provide helpful error message."""
        if v is None:
            return None

        if not v.strip():
            raise ValueError(
                "GitLab Personal Access Token cannot be empty. "
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

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, v: str | None) -> str | None:
        """Validate GitHub token format and provide helpful error message."""
        if v is None:
            return None

        if not v.strip():
            raise ValueError(
                "GitHub Personal Access Token cannot be empty. "
                "Get one at: https://github.com/settings/tokens "
                "with scopes: repo, read:org. "
                "Set it as GITHUB_TOKEN environment variable or in .env file."
            )

        v = v.strip()

        # Allow test tokens (common patterns used in testing)
        test_patterns = ("test", "mock", "fake", "dummy", "example")
        if any(pattern in v.lower() for pattern in test_patterns):
            return v

        # Validate format for real GitHub tokens
        # GitHub classic tokens start with 'ghp_', fine-grained tokens start with 'github_pat_'
        if len(v) > 20 and not any(pattern in v.lower() for pattern in test_patterns):
            if not v.startswith(
                ("ghp_", "github_pat_", "gho_", "ghu_", "ghs_", "ghr_")
            ):
                raise ValueError(
                    f"GitHub token format appears invalid: '{v[:12]}...'. "
                    "GitHub tokens typically start with: ghp_ (personal), "
                    "github_pat_ (fine-grained), gho_ (OAuth), ghu_ (user), "
                    "ghs_ (server), or ghr_ (refresh). "
                    "Get a valid token at: https://github.com/settings/tokens"
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
            # Auto-detect platform if not explicitly specified
            if not data.get("platform_provider"):
                data["platform_provider"] = cls._detect_platform_from_environment()

            # Get platform provider (with auto-detection or explicit value)
            platform_provider = data.get("platform_provider", PlatformProvider.GITLAB)
            if isinstance(platform_provider, str):
                platform_provider = PlatformProvider(platform_provider)

            # Validate platform-specific token requirements
            if platform_provider == PlatformProvider.GITLAB:
                gitlab_token = data.get("gitlab_token")
                if not gitlab_token or (
                    isinstance(gitlab_token, str) and not gitlab_token.strip()
                ):
                    raise ValueError(
                        "GitLab Personal Access Token is required for GitLab platform. "
                        "Get one at: https://gitlab.com/-/profile/personal_access_tokens "
                        "with scopes: api, read_user, read_repository. "
                        "Set it as GITLAB_TOKEN environment variable or in .env file."
                    )
            elif platform_provider == PlatformProvider.LOCAL:
                # LOCAL platform doesn't require tokens, but validate git repository
                import os
                from pathlib import Path

                # Check if we're in a git repository (only when not testing)
                current_dir = Path.cwd()
                git_dir = current_dir / ".git"
                is_git_repo = git_dir.exists() or any(
                    (parent / ".git").exists() for parent in current_dir.parents
                )

                if not is_git_repo and not os.getenv("PYTEST_CURRENT_TEST"):
                    raise ValueError(
                        "LOCAL platform requires running from within a git repository. "
                        "Please run the command from a directory that contains a .git folder."
                    )
            elif platform_provider == PlatformProvider.GITHUB:
                github_token = data.get("github_token")
                if not github_token or (
                    isinstance(github_token, str) and not github_token.strip()
                ):
                    raise ValueError(
                        "GitHub Personal Access Token is required for GitHub platform. "
                        "Get one at: https://github.com/settings/tokens "
                        "with scopes: repo, read:org. "
                        "Set it as GITHUB_TOKEN environment variable or in .env file."
                    )

            # Set default model based on provider if model not explicitly set
            provider_str = data.get("ai_provider")
            model = data.get("ai_model")

            # Only set default if model is None (not provided at all)
            if model is None:
                # If no provider specified, use the default provider (GEMINI)
                if provider_str is None:
                    provider = AIProvider.GEMINI  # Default provider
                elif isinstance(provider_str, str):
                    try:
                        provider = AIProvider(provider_str)
                    except ValueError:
                        # Invalid provider, let other validators handle it
                        provider = None
                else:
                    provider = provider_str  # Already an AIProvider enum

                # Set default model for the provider
                if provider is not None:
                    data["ai_model"] = get_default_model_for_provider(provider)

        return data

    @staticmethod
    def _detect_platform_from_environment() -> PlatformProvider:
        """Auto-detect platform based on CI/CD environment variables.

        Returns:
            PlatformProvider: Detected platform (GitLab or GitHub)

        Detection logic:
        - GitLab CI: GITLAB_CI=true AND CI_PROJECT_PATH exists (primary)
        - GitHub Actions: GITHUB_ACTIONS=true AND GITHUB_REPOSITORY exists (primary)
        - Fallback: GITHUB_REPOSITORY exists (GitHub) or CI_PROJECT_PATH exists (GitLab)
        - Default: GitLab (backward compatibility)
        """
        import os

        # GitLab CI detection (require both GITLAB_CI and data availability)
        if os.getenv("GITLAB_CI") == "true" and os.getenv("CI_PROJECT_PATH"):
            return PlatformProvider.GITLAB

        # GitHub Actions detection (require both GITHUB_ACTIONS and data availability)
        if os.getenv("GITHUB_ACTIONS") == "true" and os.getenv("GITHUB_REPOSITORY"):
            return PlatformProvider.GITHUB

        # Fallback: detect by data availability only (safer for edge cases)
        if os.getenv("GITHUB_REPOSITORY"):
            return PlatformProvider.GITHUB
        if os.getenv("CI_PROJECT_PATH"):
            return PlatformProvider.GITLAB

        # Default to GitLab for backward compatibility
        return PlatformProvider.GITLAB

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
            # Gemini should use valid gemini models
            # Valid models based on https://ai.google.dev/gemini-api/docs/models
            valid_gemini_models = {
                # Current models
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                # Deprecated but still available
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
            }

            # Also allow versioned models (e.g., gemini-2.5-pro-001) and preview models
            is_valid_model = (
                model in valid_gemini_models
                or any(
                    model.startswith(valid_model + "-")
                    for valid_model in valid_gemini_models
                )
                or "preview" in model
                or "exp" in model  # Preview/experimental variants
            )

            if not is_valid_model:
                suggested_model = "gemini-2.5-pro"
                raise ValueError(
                    f"AI model '{model}' is not a valid Gemini model. "
                    f"Valid models include: {', '.join(sorted(valid_gemini_models))}. "
                    f"For current recommendation, try '{suggested_model}'. "
                    f"Or change ai_provider to match your model choice."
                )

        return config

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",
    }

    def get_effective_repository_path(self) -> str | None:
        """Get effective repository path from CI environment or explicit config."""
        # Priority: new fields -> legacy GitLab fields -> None
        return self.repository_path or self.ci_project_path

    def get_effective_pull_request_number(self) -> int | None:
        """Get effective pull/merge request number from CI environment or explicit config."""
        # Priority: new fields -> legacy GitLab fields -> None
        return self.pull_request_number or self.ci_merge_request_iid

    def get_effective_server_url(self) -> str:
        """Get effective server URL prioritizing CI environment."""
        # Priority: new fields -> legacy GitLab fields -> platform defaults
        if self.server_url:
            return self.server_url
        if self.ci_server_url:
            return self.ci_server_url

        # Return platform-specific default
        if self.platform_provider == PlatformProvider.GITHUB:
            return self.github_url
        else:
            return self.gitlab_url

    def get_platform_token(self) -> str:
        """Get the appropriate token for the configured platform."""
        if self.platform_provider == PlatformProvider.GITLAB:
            if not self.gitlab_token:
                raise ValueError("GitLab token is required for GitLab platform")
            return self.gitlab_token
        elif self.platform_provider == PlatformProvider.GITHUB:
            if not self.github_token:
                raise ValueError("GitHub token is required for GitHub platform")
            return self.github_token
        else:
            raise ValueError(f"Unsupported platform: {self.platform_provider}")

    def is_ci_mode(self) -> bool:
        """Check if running in CI/CD environment."""
        return bool(
            self.get_effective_repository_path()
            and self.get_effective_pull_request_number()
        )

    # Legacy methods for backward compatibility
    def get_effective_project_id(self) -> str | None:
        """Get effective project ID from CI environment (legacy GitLab method)."""
        return self.get_effective_repository_path()

    def get_effective_mr_iid(self) -> int | None:
        """Get effective MR IID from CI environment (legacy GitLab method)."""
        return self.get_effective_pull_request_number()

    def get_effective_gitlab_url(self) -> str:
        """Get effective GitLab URL (legacy method)."""
        if self.platform_provider != PlatformProvider.GITLAB:
            raise ValueError(
                "get_effective_gitlab_url() only valid for GitLab platform"
            )
        return self.get_effective_server_url()
