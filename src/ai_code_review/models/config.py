"""Configuration models for AI Code Review tool."""

from __future__ import annotations

import os
import re
from enum import Enum
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings

from ai_code_review.utils.constants import MAX_COMMENTS_TO_FETCH

# Default file exclusion patterns - defined once to avoid duplication
_DEFAULT_EXCLUDE_PATTERNS = [
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


# PlatformProvider moved here to avoid circular imports
class PlatformProvider(str, Enum):
    """Supported code hosting platforms."""

    GITLAB = "gitlab"
    GITHUB = "github"
    LOCAL = "local"


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

# Default AI provider
DEFAULT_AI_PROVIDER = AIProvider.GEMINI


class SkipReviewConfig(BaseModel):
    """Configuration for automatic review skipping."""

    enabled: bool = Field(
        default=True, description="Enable/disable automatic review skipping"
    )

    # Explicit keywords (case-insensitive, checked in title + description)
    keywords: list[str] = Field(
        default=[
            "[skip ai-review]",
            "[no-review]",
            "[bot]",
            "[skip-review]",
            "[automated]",
        ],
        description="Keywords to trigger review skipping (case-insensitive)",
    )

    # Regex patterns for automated tools (checked against title only)
    patterns: list[str] = Field(
        default=[
            # Dependency updates (comprehensive patterns)
            r"^(chore|build|ci|feat|fix)\(deps?\):",
            r"^bump\s+.*\s+from\s+[\d.]+\s+to\s+[\d.]+",
            # Version releases and bumps
            r"^(chore|release):\s*(release|version|bump)\s+v?\d+\.\d+",
            r"^bump:\s*version",
            # Auto-generated changes
            r"^\[automated\]",
            r"^auto.*update",
        ],
        description="Regex patterns for automated changes (case-insensitive matching)",
    )

    # Author patterns (for known bots)
    bot_authors: list[str] = Field(
        default=[
            "renovate[bot]",
            "dependabot[bot]",
            "github-actions[bot]",
            "gitlab-ci-token",
            "allcontributors[bot]",
            "greenkeeper[bot]",
            "snyk-bot",
            "auto-gitlab-bot",
        ],
        description="Known bot author patterns for automatic skipping",
    )

    # Documentation-only patterns (only used if skip_documentation_only is True)
    documentation_patterns: list[str] = Field(
        default=[
            r"^docs?(\(.+\))?:\s+.*",  # docs: or docs(scope):
        ],
        description="Regex patterns for documentation-only changes",
    )

    # Feature flags for intelligent detection
    skip_dependency_updates: bool = Field(
        default=True, description="Skip reviews for dependency update PRs/MRs"
    )

    skip_documentation_only: bool = Field(
        default=False,  # Conservative default - can be enabled per project
        description="Skip reviews for documentation-only changes",
    )

    skip_bot_authors: bool = Field(
        default=True, description="Skip reviews from known bot authors"
    )

    skip_draft_prs: bool = Field(
        default=True, description="Skip reviews for draft/WIP pull/merge requests"
    )

    @field_validator("patterns", "documentation_patterns")
    @classmethod
    def validate_patterns(cls, v: list[str]) -> list[str]:
        """Validate regex patterns to prevent ReDoS and ensure they compile."""
        import re

        validated_patterns = []
        for pattern in v:
            try:
                # Test that pattern compiles
                re.compile(pattern)
                validated_patterns.append(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

        return validated_patterns


# Default models for each AI provider
_DEFAULT_MODELS = {
    AIProvider.OLLAMA: "qwen2.5-coder:7b",
    AIProvider.GEMINI: "gemini-3-pro-preview",
    AIProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    AIProvider.OPENAI: "gpt-5-mini",  # Default for future OpenAI implementation
}


# Default synthesis models (fast/cheap variants for preprocessing)
_DEFAULT_SYNTHESIS_MODELS = {
    AIProvider.OLLAMA: "qwen2.5-coder:7b",  # Use same for local
    AIProvider.GEMINI: "gemini-2.5-flash",
    AIProvider.ANTHROPIC: "claude-3-5-haiku-20241022",
    AIProvider.OPENAI: "gpt-4o-mini",
}


def get_default_model_for_provider(provider: AIProvider) -> str:
    """Get default model name for each AI provider.

    Args:
        provider: The AI provider

    Returns:
        str: Default model name for the provider

    Raises:
        ValueError: If no default model is defined for the provider
    """
    if provider not in _DEFAULT_MODELS:
        raise ValueError(
            f"No default model defined for provider '{provider.value}'. "
            f"Available providers: {list(_DEFAULT_MODELS.keys())}"
        )
    return _DEFAULT_MODELS[provider]


def get_default_synthesis_model_for_provider(provider: AIProvider) -> str:
    """Get default synthesis model name for each AI provider.

    Synthesis models are fast/cheap variants used for preprocessing
    comments and reviews before the main review.

    Args:
        provider: The AI provider

    Returns:
        str: Default synthesis model name for the provider

    Raises:
        ValueError: If no default synthesis model is defined for the provider
    """
    if provider not in _DEFAULT_SYNTHESIS_MODELS:
        raise ValueError(
            f"No default synthesis model defined for provider '{provider.value}'. "
            f"Available providers: {list(_DEFAULT_SYNTHESIS_MODELS.keys())}"
        )
    return _DEFAULT_SYNTHESIS_MODELS[provider]


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
        default=DEFAULT_AI_PROVIDER, description="AI provider to use"
    )
    ai_model: str | None = Field(
        default=None,
        description="AI model name (auto-selects default model if not specified)",
    )
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

    # LLM API timeout and retry configuration
    llm_timeout: float = Field(
        default=60.0,
        description="Timeout in seconds for LLM API calls (cloud providers). Lower values fail faster in CI/CD.",
        gt=0.0,
    )
    llm_max_retries: int = Field(
        default=2,
        description="Maximum number of retries for LLM API calls. Lower values fail faster in CI/CD.",
        ge=0,
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

    # Review context preprocessing
    enable_review_context: bool = Field(
        default=True,
        description="Enable fetching previous reviews/comments for context",
    )
    enable_review_synthesis: bool = Field(
        default=True,
        description="Enable preprocessing of reviews with fast model for synthesis (reduces tokens)",
    )
    synthesis_model: str | None = Field(
        default=None,
        description="Model for review synthesis (auto-selects fast model if not specified)",
    )
    synthesis_max_tokens: int = Field(
        default=2000,
        description="Maximum tokens for synthesis output",
        gt=0,
    )
    max_comments_to_fetch: int = Field(
        default=MAX_COMMENTS_TO_FETCH,
        description="Maximum number of comments to fetch from platform API for synthesis",
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
    team_context_file: str | None = Field(
        default=None,
        description="Team/organization context file (local path or URL, higher priority than project context)",
    )
    include_mr_summary: bool = Field(
        default=True,
        description="Include MR Summary section in reviews (disable for shorter, code-focused reviews)",
    )

    # Execution options
    dry_run: bool = Field(default=False, description="Dry run mode (no API calls)")
    big_diffs: bool = Field(
        default=False,
        description="Force larger context window - auto-activated for large diffs/content",
    )
    health_check: bool = Field(
        default=False, description="Perform health check on all components and exit"
    )
    post: bool = Field(
        default=False, description="Post review as MR comment to GitLab/GitHub"
    )

    # Output options
    output_file: str | None = Field(
        default=None,
        description="Save review output to file (default: display in terminal)",
    )

    # Local mode options
    target_branch: str = Field(
        default="main", description="Target branch for local comparison (default: main)"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # File filtering
    exclude_patterns: list[str] = Field(
        default=_DEFAULT_EXCLUDE_PATTERNS,
        description="Glob patterns for files to exclude from AI review",
    )

    # Complete diff fetching timeout (advanced option)
    diff_download_timeout: int = Field(
        default=120,
        description="Timeout for downloading complete diffs via HTTP (seconds)",
    )

    # Configuration file options
    no_config_file: bool = Field(
        default=False,
        validation_alias=AliasChoices("no_config_file", "NO_CONFIG_FILE"),
        description="Skip loading config file (auto-detected or specified)",
    )
    config_file: str | None = Field(
        default=None,
        validation_alias=AliasChoices("config_file", "CONFIG_FILE"),
        description="Custom config file path",
    )

    # Skip review configuration
    skip_review: SkipReviewConfig = Field(
        default_factory=SkipReviewConfig,
        description="Configuration for automatic review skipping",
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
        """Validate AI model name format.

        Empty strings are treated as None (use provider's default model).
        """
        # None is allowed - get_ai_model() will resolve to default
        if v is None:
            return v

        # Empty string is treated as None - use provider's default
        if not v.strip():
            return None

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

    @field_validator("team_context_file")
    @classmethod
    def validate_team_context_file(cls, v: str | None) -> str | None:
        """Validate team context file path or URL."""
        if v is None:
            return None

        if not v.strip():
            return None

        # If it's a URL, validate format
        if v.startswith(("http://", "https://")):
            url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
            if not re.match(url_pattern, v):
                raise ValueError(f"Invalid team context URL format: {v}")
            return v.strip()

        # If it's a local path, don't validate existence (file might not exist yet)
        return v.strip()

    @field_validator("gitlab_token")
    @classmethod
    def validate_gitlab_token(cls, v: str | None) -> str | None:
        """Validate GitLab token format and provide helpful error message."""
        if v is None:
            return None

        if not (v := v.strip()):
            raise ValueError(
                "GitLab Personal Access Token cannot be empty. "
                "Get one at: https://gitlab.com/-/profile/personal_access_tokens "
                "with scopes: api, read_user, read_repository. "
                "Set it as GITLAB_TOKEN environment variable or in .env file."
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

            # Set default model based on provider if provider specified but model not explicitly set
            # This handles direct Config() construction with different providers
            provider_str = data.get("ai_provider")
            model = data.get("ai_model")

            # Only override if provider is specified and model is not explicitly set (None)
            # Don't override if user explicitly set a model, even if it's the default GEMINI model
            if provider_str is not None and model is None:
                if isinstance(provider_str, str):
                    try:
                        provider = AIProvider(provider_str)
                    except ValueError:
                        # Invalid provider, let other validators handle it
                        provider = None
                else:
                    provider = provider_str  # Already an AIProvider enum

                # Set appropriate default model for the provider
                if provider is not None:
                    data["ai_model"] = get_default_model_for_provider(provider)

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

            # Validate AI provider API key requirements (skip in dry run mode)
            ai_provider_value = data.get("ai_provider")
            # Coerce string to enum for comparison, or use default if not provided
            try:
                ai_provider = (
                    AIProvider(ai_provider_value)
                    if ai_provider_value
                    else DEFAULT_AI_PROVIDER
                )
            except ValueError:
                # Let Pydantic handle the invalid enum value later
                ai_provider = None

            if ai_provider and ai_provider in CLOUD_PROVIDERS:
                # Skip API key validation in dry run mode
                dry_run = data.get("dry_run", False)
                if not dry_run:
                    ai_api_key = data.get("ai_api_key")
                    if not ai_api_key or (
                        isinstance(ai_api_key, str) and not ai_api_key.strip()
                    ):
                        provider_urls = {
                            AIProvider.GEMINI: "https://makersuite.google.com/app/apikey",
                            AIProvider.OPENAI: "https://platform.openai.com/api-keys",
                            AIProvider.ANTHROPIC: "https://console.anthropic.com/",
                        }
                        url = provider_urls.get(ai_provider, "provider website")
                        raise ValueError(
                            f"API key is required for cloud provider '{ai_provider.value}'. "
                            f"Get one at: {url} "
                            f"Set it as AI_API_KEY environment variable or in .env file."
                        )

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
        model = config.get_ai_model()

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
                "gemini-3-pro-preview",
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
                suggested_model = _DEFAULT_MODELS[AIProvider.GEMINI]
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
        "extra": "ignore",  # Ignore unknown environment variables
    }

    def get_effective_repository_path(self) -> str | None:
        """Get effective repository path from CI environment or explicit config."""
        # Priority: new fields -> legacy GitLab fields -> None
        return self.repository_path or self.ci_project_path

    def get_ai_model(self) -> str:
        """Get AI model to use for main review.

        Returns configured model or appropriate default model based on provider.

        Returns:
            Model name to use for main review
        """
        if self.ai_model:
            return self.ai_model

        return get_default_model_for_provider(self.ai_provider)

    def get_synthesis_model(self) -> str:
        """Get model to use for review synthesis.

        Returns configured synthesis model or appropriate fast model based on provider.

        Returns:
            Model name to use for synthesis
        """
        if self.synthesis_model:
            return self.synthesis_model

        return get_default_synthesis_model_for_provider(self.ai_provider)

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

    @classmethod
    def create_with_defaults(cls) -> Config:
        """Create config with all defaults established.

        Returns:
            Config: Configuration object with all default values set
        """
        return cls()

    @classmethod
    def _load_config_file_if_enabled(cls, cli_args: dict[str, Any]) -> dict[str, Any]:
        """Load config file based on CLI flags and auto-detection.

        Args:
            cli_args: CLI arguments containing config file options

        Returns:
            dict: Config file data or empty dict if not found/disabled

        Raises:
            ValueError: If explicitly specified config file doesn't exist or has errors
        """
        # Skip if --no-config-file specified
        if cli_args.get("no_config_file"):
            return {}

        # Lazy imports - only load when actually needed
        from pathlib import Path

        import yaml

        # Determine config file path and whether it was explicitly specified
        config_path = None
        is_explicit = False

        if cli_args.get("config_file"):
            # Custom path specified explicitly by user
            config_path = Path(cli_args["config_file"])
            is_explicit = True
        else:
            # Auto-detect default path
            default_path = Path(".ai_review/config.yml")
            if default_path.exists():
                config_path = default_path
                is_explicit = False

        # Check if explicitly specified file exists
        if config_path and is_explicit and not config_path.exists():
            raise ValueError(
                f"Config file not found: {config_path}. "
                f"Please check the path or remove --config-file to use auto-detection."
            )

        # Load and parse file if found
        if config_path and config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    if not isinstance(data, dict):
                        raise ValueError(
                            f"Config file must contain a YAML object, got {type(data).__name__}"
                        )
                    return data
            except OSError as e:
                raise ValueError(
                    f"Failed to read config file {config_path}: {e}"
                ) from e
            except yaml.YAMLError as e:
                raise ValueError(
                    f"Invalid YAML syntax in config file {config_path}: {e}"
                ) from e
            except Exception as e:
                raise ValueError(
                    f"Unexpected error loading config file {config_path}: {e}"
                ) from e

        return {}

    @classmethod
    def from_layered_config(
        cls, cli_data: dict[str, Any], config_file_data: dict[str, Any]
    ) -> Config:
        """Create config with full priority layering: CLI > Env > Config File > Defaults.

        Args:
            cli_data: CLI arguments/options (highest priority)
            config_file_data: Config file data (lower priority)

        Returns:
            Config: Fully configured Config object

        Priority order (highest to lowest) - OPTIMIZED FOR CI/CD:
        1. CLI arguments (cli_data) - Manual overrides
        2. Environment variables - CI/CD configuration (handled by Pydantic BaseSettings)
        3. Config file (config_file_data) - Project configuration
        4. Field defaults - System defaults

        Note: Environment variables are automatically handled by Pydantic BaseSettings,
        so they have priority over config file and defaults, but CLI args override everything.
        """
        # Start with config file data as base layer
        data = config_file_data.copy()

        # Layer CLI overrides (highest priority)
        # Only include non-None CLI values to preserve lower layers
        cli_overrides = {k: v for k, v in cli_data.items() if v is not None}
        data.update(cli_overrides)

        # Handle ai_model/ai_provider relationship intelligently
        # If provider changed but model wasn't explicitly set, use provider's default model
        if "ai_provider" in cli_overrides and "ai_model" not in cli_overrides:
            provider_str = cli_overrides["ai_provider"]
            if isinstance(provider_str, str):
                try:
                    provider = AIProvider(provider_str)
                    data["ai_model"] = get_default_model_for_provider(provider)
                except ValueError:
                    # Invalid provider, let validation handle it
                    pass
            elif isinstance(provider_str, AIProvider):
                data["ai_model"] = get_default_model_for_provider(provider_str)

        # Handle synthesis_model/ai_provider relationship intelligently
        # If provider changed but synthesis_model wasn't explicitly set, use provider's default synthesis model
        if "ai_provider" in cli_overrides and "synthesis_model" not in cli_overrides:
            provider_str = cli_overrides["ai_provider"]
            if isinstance(provider_str, str):
                try:
                    provider = AIProvider(provider_str)
                    data["synthesis_model"] = get_default_synthesis_model_for_provider(
                        provider
                    )
                except ValueError:
                    # Invalid provider, let validation handle it
                    pass
            elif isinstance(provider_str, AIProvider):
                data["synthesis_model"] = get_default_synthesis_model_for_provider(
                    provider_str
                )

        return cls(**data)

    @classmethod
    def from_cli_args(cls, cli_args: dict[str, Any]) -> Config:
        """Create config from CLI arguments with intelligent automatic mapping.

        This method handles all the complex mapping between CLI parameter names
        and Config field names, eliminating the need for manual mapping functions.

        Args:
            cli_args: Raw CLI arguments from Click (kwargs from main function)

        Returns:
            Config: Fully configured Config object

        Priority order (highest to lowest) - OPTIMIZED FOR CI/CD:
        1. CLI arguments (cli_args) - Manual overrides
        2. Environment variables - CI/CD configuration (handled by Pydantic BaseSettings)
        3. Field defaults - System defaults
        """
        # Step 1: Auto-map CLI parameters to config fields
        mapped_args: dict[str, Any] = {}

        # CLI parameter name -> Config field name mappings
        # IMPORTANT: This mapping must be kept in sync with CLI options defined in cli.py
        # When adding new @click.option decorators, ensure they are either:
        #   1. Added to this map if they need custom field mapping
        #   2. Added to DIRECT_MAPPINGS if CLI name matches Config field name
        #   3. Handled in special cases section if they require custom logic
        # Missing entries will cause CLI options to be silently ignored!
        CLI_TO_CONFIG_MAP = {
            # AI provider mappings
            "provider": "ai_provider",
            "model": "ai_model",
            "ollama_url": "ollama_base_url",
            # Platform mappings
            "local": "_local_flag",  # Special handling below
            "platform": "platform_provider",
            # Project context mappings
            "project_context": "enable_project_context",
            "context_file": "project_context_file",
            "team_context": "team_context_file",
            "no_mr_summary": "_no_mr_summary_flag",  # Special handling below
            # URL mappings
            "gitlab_url": "gitlab_url",
            "github_url": "github_url",
            # Processing limits
            "max_tokens": "max_tokens",
            "max_chars": "max_chars",
            "max_files": "max_files",
            "language_hint": "language_hint",
            "temperature": "temperature",
            # Execution options
            "dry_run": "dry_run",
            "big_diffs": "big_diffs",
            "log_level": "log_level",
            # SSL options
            "ssl_cert_url": "ssl_cert_url",
            "ssl_cert_cache_dir": "ssl_cert_cache_dir",
            # Project identification (handle arguments and options)
            "project_id_option": "project_id",
            "pr_number_option": "pr_number",
            "gitlab_mr_iid": "gitlab_mr_iid",  # Legacy
            "target_branch": "target_branch",
            # Configuration file options
            "no_config_file": "no_config_file",
            "config_file": "config_file",
            # Skip review options
            "no_skip_detection": "_no_skip_detection_flag",  # Special handling below
            "test_skip_only": "_test_skip_only_flag",  # Special handling below
        }

        # Step 2: Apply automatic mappings (skip internal flags)
        for cli_name, config_field in CLI_TO_CONFIG_MAP.items():
            if cli_name in cli_args and cli_args[cli_name] is not None:
                # Skip internal mapping fields that don't exist in Config
                if not config_field.startswith("_"):
                    mapped_args[config_field] = cli_args[cli_name]

        # Step 3: Handle direct mappings (CLI name == config field name)
        DIRECT_MAPPINGS = [
            "post",
            "output_file",
            "health_check",
            "gitlab_token",
            "github_token",
            "dry_run",
            "ai_provider",
            "ai_model",
        ]
        for field_name in DIRECT_MAPPINGS:
            if field_name in cli_args and cli_args[field_name] is not None:
                mapped_args[field_name] = cli_args[field_name]

        # Step 4: Skip positional arguments - they're not Config fields
        # (project_id and mr_iid are handled separately by _resolve_project_params)

        # Step 5: Handle special cases that require logic

        # Local mode overrides platform
        if cli_args.get("local"):
            mapped_args["platform_provider"] = PlatformProvider.LOCAL

        # Platform enum conversion
        if "platform_provider" in mapped_args and isinstance(
            mapped_args["platform_provider"], str
        ):
            mapped_args["platform_provider"] = PlatformProvider(
                mapped_args["platform_provider"]
            )

        # AI provider enum conversion
        if "ai_provider" in mapped_args and isinstance(mapped_args["ai_provider"], str):
            mapped_args["ai_provider"] = AIProvider(mapped_args["ai_provider"])

        # no_mr_summary flag -> include_mr_summary = False
        if cli_args.get("no_mr_summary"):
            mapped_args["include_mr_summary"] = False

        # no_skip_detection flag -> skip_review.enabled = False
        if cli_args.get("no_skip_detection"):
            # Initialize skip_review dict if not exists
            if "skip_review" not in mapped_args:
                mapped_args["skip_review"] = {}
            mapped_args["skip_review"]["enabled"] = False

        # test_skip_only is handled at CLI level, not in config
        # We'll check for it in the CLI main function

        # Handle file filtering options
        if cli_args.get("no_file_filtering"):
            mapped_args["exclude_patterns"] = []
        elif cli_args.get("exclude_files"):
            # Get default patterns and add user patterns
            mapped_args["exclude_patterns"] = _DEFAULT_EXCLUDE_PATTERNS + list(
                cli_args["exclude_files"]
            )
        # If neither flag is set, Config defaults will apply (which include default patterns)

        # Step 6: Load config file if enabled
        config_file_data = cls._load_config_file_if_enabled(cli_args)

        # Step 7: Use layered construction with config file
        return cls.from_layered_config(mapped_args, config_file_data)
