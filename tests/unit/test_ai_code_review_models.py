"""Tests for data models."""

from __future__ import annotations

from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from ai_code_review.models.config import AIProvider, Config, PlatformProvider
from ai_code_review.models.platform import (
    PullRequestCommit,
    PullRequestData,
    PullRequestDiff,
    PullRequestInfo,
)
from ai_code_review.models.review import CodeReview, FileReview, ReviewResult


def clear_config_env_vars(monkeypatch: MonkeyPatch) -> None:
    """Clear all configuration-related environment variables and disable .env file for test isolation."""
    # Clear environment variables
    env_vars_to_clear = [
        "PLATFORM_PROVIDER",
        "GITLAB_URL",
        "GITLAB_TOKEN",
        "GITHUB_URL",
        "GITHUB_TOKEN",
        "AI_PROVIDER",
        "AI_MODEL",
        "AI_API_KEY",
        "SSL_VERIFY",
        "SSL_CERT_PATH",
        "REPOSITORY_PATH",
        "PULL_REQUEST_NUMBER",
        "SERVER_URL",
        "CI_PROJECT_PATH",
        "CI_MERGE_REQUEST_IID",
        "CI_SERVER_URL",
        "GITHUB_REPOSITORY",  # GitHub Actions auto-detection
        "GITHUB_SERVER_URL",  # GitHub Enterprise
        "GITLAB_CI",  # GitLab CI detection
        "GITHUB_ACTIONS",  # GitHub Actions detection
        "TEMPERATURE",
        "MAX_TOKENS",
        "HTTP_TIMEOUT",
        "OLLAMA_BASE_URL",
        "MAX_CHARS",
        "MAX_FILES",
        "LANGUAGE_HINT",
        "DRY_RUN",
        "BIG_DIFFS",
        "LOG_LEVEL",
        "ENABLE_PROJECT_CONTEXT",
        "PROJECT_CONTEXT_FILE",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)

    # Disable .env file loading by pointing to a non-existent file
    # This prevents pydantic_settings from reading the actual .env file
    monkeypatch.setattr(
        "ai_code_review.models.config.Config.model_config",
        {
            "env_file": ".env.nonexistent",
            "env_file_encoding": "utf-8",
            "case_sensitive": False,
            "env_prefix": "",
        },
    )


class TestConfig:
    """Test configuration model."""

    def test_config_creation_with_minimal_required_fields(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test creating config with only required fields for Ollama."""
        # Clear environment variables that could interfere with test isolation
        clear_config_env_vars(monkeypatch)

        # Use Ollama to avoid API key requirement
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
        )

        assert config.gitlab_token == "test_token"
        assert config.gitlab_url == "https://gitlab.com"
        assert config.platform_provider == PlatformProvider.GITLAB  # Default
        assert config.ai_provider == AIProvider.OLLAMA
        assert config.ai_model == "qwen2.5-coder:7b"  # Specified model for Ollama
        # API key may be set from environment, that's fine for Ollama

    def test_config_custom_values(self) -> None:
        """Test config with custom values."""
        config = Config(
            gitlab_token="custom_token",
            gitlab_url="https://custom-gitlab.com",
            ai_provider=AIProvider.GEMINI,
            ai_model="gemini-2.5-pro",
            ai_api_key="test_api_key",
        )

        assert config.gitlab_token == "custom_token"
        assert config.gitlab_url == "https://custom-gitlab.com"
        assert config.platform_provider == PlatformProvider.GITLAB  # Default
        assert config.ai_provider == AIProvider.GEMINI
        assert config.ai_model == "gemini-2.5-pro"
        assert config.ai_api_key == "test_api_key"

    def test_config_github_platform(self, monkeypatch: MonkeyPatch) -> None:
        """Test config with GitHub platform."""
        # Clear environment variables to avoid interference
        clear_config_env_vars(monkeypatch)

        config = Config(
            platform_provider=PlatformProvider.GITHUB,
            github_token="ghp_test_token",
            ai_provider=AIProvider.GEMINI,
            ai_model="gemini-2.5-pro",
            ai_api_key="test_api_key",
        )

        assert config.platform_provider == PlatformProvider.GITHUB
        assert config.github_token == "ghp_test_token"
        assert config.github_url == "https://api.github.com"  # Default
        assert config.gitlab_token is None  # Not required for GitHub
        assert config.ai_provider == AIProvider.GEMINI
        assert config.ai_model == "gemini-2.5-pro"

    def test_config_ai_model_parameters(self, monkeypatch: MonkeyPatch) -> None:
        """Test AI model parameter configuration."""
        clear_config_env_vars(monkeypatch)

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
            temperature=0.5,
            max_tokens=2048,
        )

        assert config.temperature == 0.5
        assert config.max_tokens == 2048

    def test_dry_run_defaults_false(self, monkeypatch: MonkeyPatch) -> None:
        """Test that dry_run defaults to False."""
        clear_config_env_vars(monkeypatch)

        # Use Ollama to avoid API key requirement
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        assert config.dry_run is False
        # Test default values for new fields
        assert config.temperature == 0.1
        assert config.max_tokens == 8000

    @pytest.mark.allow_env_file
    def test_config_env_file_loading(self, chdir_tmp, monkeypatch: MonkeyPatch) -> None:
        """Test that config can load from .env file."""

        # Clear all environment variables that could interfere
        env_vars_to_clear = [
            "GITLAB_TOKEN",
            "GITLAB_URL",
            "AI_PROVIDER",
            "AI_MODEL",
            "AI_API_KEY",
            "TEMPERATURE",
            "MAX_TOKENS",
            "HTTP_TIMEOUT",
            "OLLAMA_BASE_URL",
            "MAX_CHARS",
            "MAX_FILES",
            "LANGUAGE_HINT",
            "DRY_RUN",
            "LOG_LEVEL",
            "CI_PROJECT_PATH",
            "CI_MERGE_REQUEST_IID",
            "CI_SERVER_URL",
        ]

        for var in env_vars_to_clear:
            monkeypatch.delenv(var, raising=False)

        # Create a temporary .env file
        env_file = chdir_tmp / ".env"
        env_content = """
GITLAB_TOKEN=env-token
AI_PROVIDER=openai
AI_API_KEY=test-openai-key
TEMPERATURE=0.7
MAX_TOKENS=2048
DRY_RUN=true
"""
        env_file.write_text(env_content.strip())

        # Change to test directory with fixture
        config = Config()  # type: ignore[call-arg] # Config loads from .env file
        assert config.gitlab_token == "env-token"
        assert config.ai_provider.value == "openai"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.dry_run is True

    def test_config_url_validation(self) -> None:
        """Test URL validation for gitlab_url and ollama_base_url."""

        # Valid URLs should work
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
            gitlab_url="https://gitlab.example.com",
            ollama_base_url="http://localhost:11434",
        )
        assert config.gitlab_url == "https://gitlab.example.com"
        assert config.ollama_base_url == "http://localhost:11434"

        # Invalid URLs should raise ValueError
        with pytest.raises(ValueError, match="Invalid URL format"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
                ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
                gitlab_url="not-a-url",
            )

        with pytest.raises(ValueError, match="Invalid URL format"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
                ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
                ollama_base_url="ftp://invalid",
            )

    def test_config_url_validation_errors(self) -> None:
        """Test URL validation error cases - hits line 244."""
        # Test empty URL - hits line 244
        with pytest.raises(ValueError, match="URL cannot be empty"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                gitlab_url="",  # Empty URL
            )

    def test_config_ssl_validation_errors(self, tmp_path: Path) -> None:
        """Test SSL certificate validation error cases - hits lines 268, 280, 284."""
        # Test SSL cert file not found (more reliable than chmod in CI)
        ssl_file = tmp_path / "nonexistent.pem"  # File doesn't exist

        with pytest.raises(ValueError, match="SSL certificate file not found"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ssl_cert_path=str(ssl_file),
            )

        # Test empty SSL cert URL - hits line 280
        with pytest.raises(ValueError, match="SSL certificate URL cannot be empty"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ssl_cert_url="   ",  # Whitespace only
            )

        # Test invalid SSL cert URL format - hits line 284
        with pytest.raises(ValueError, match="Invalid SSL certificate URL format"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ssl_cert_url="invalid_ssl_url",
            )

    def test_config_ai_model_validation(self) -> None:
        """Test AI model name validation."""

        # Valid model names should work
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Changed to valid Ollama model
        )
        assert config.ai_model == "qwen2.5-coder:7b"

        config2 = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model=" qwen2.5-coder:7b ",
        )
        assert config2.ai_model == "qwen2.5-coder:7b"  # Should be trimmed

        # Empty strings are normalized to None (use provider's default)
        config_empty = Config(
            gitlab_token="test_token", ai_provider=AIProvider.OLLAMA, ai_model=""
        )
        assert config_empty.ai_model is None
        assert config_empty.get_ai_model() == "qwen2.5-coder:7b"  # Default for Ollama

        config_spaces = Config(
            gitlab_token="test_token", ai_provider=AIProvider.OLLAMA, ai_model="   "
        )
        assert config_spaces.ai_model is None
        assert config_spaces.get_ai_model() == "qwen2.5-coder:7b"  # Default for Ollama

        # Model names with invalid characters should raise ValueError

        with pytest.raises(ValueError, match="invalid characters"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ai_model="model\nwith\nnewlines",
            )

        with pytest.raises(ValueError, match="invalid characters"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ai_model="model\twith\ttabs",
            )

    def test_config_log_level_validation(self) -> None:
        """Test log level validation."""

        # Valid log levels should work and be normalized to uppercase
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
            log_level="debug",
        )
        assert config.log_level == "DEBUG"

        config2 = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
            log_level="INFO",
        )
        assert config2.log_level == "INFO"

        # Invalid log level should raise ValueError
        with pytest.raises(ValueError, match="Invalid log level"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ai_model="qwen2.5-coder:7b",
                log_level="INVALID",
            )

    def test_config_ci_mode_detection(self, monkeypatch: MonkeyPatch) -> None:
        """Test CI mode detection."""
        # Clear all CI environment variables to ensure clean test
        ci_vars_to_clear = [
            "CI_PROJECT_PATH",
            "CI_MERGE_REQUEST_IID",
            "CI_SERVER_URL",
            "GITLAB_CI",
        ]
        for var in ci_vars_to_clear:
            monkeypatch.delenv(var, raising=False)

        # Not CI mode (missing CI variables)
        config = Config(
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        assert not config.is_ci_mode()

        # Not CI mode (only project path)
        config = Config(
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            ci_project_path="group/project",
        )
        assert not config.is_ci_mode()

        # CI mode (both variables present)
        config = Config(
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
            ci_project_path="group/project",
            ci_merge_request_iid=123,
        )
        assert config.is_ci_mode()

    def test_config_effective_values(self, monkeypatch: MonkeyPatch) -> None:
        """Test effective value getters for CI integration."""
        # Clear ALL CI environment variables to avoid contamination from real CI
        ci_vars_to_clear = [
            "CI_PROJECT_PATH",  # GitLab CI
            "CI_MERGE_REQUEST_IID",  # GitLab CI
            "CI_SERVER_URL",  # GitLab CI
            "GITHUB_REPOSITORY",  # GitHub Actions
            "GITHUB_SERVER_URL",  # GitHub Actions
        ]
        for var in ci_vars_to_clear:
            monkeypatch.delenv(var, raising=False)

        config = Config(
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
            gitlab_url="https://gitlab.com",
            ci_project_path="group/ci-project",
            ci_merge_request_iid=456,
            ci_server_url="https://ci-gitlab.com",
        )

        # CI values should take precedence
        assert config.get_effective_project_id() == "group/ci-project"
        assert config.get_effective_mr_iid() == 456
        assert config.get_effective_gitlab_url() == "https://ci-gitlab.com"

    def test_config_platform_autodetection_gitlab_ci(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test platform auto-detection for GitLab CI."""
        clear_config_env_vars(monkeypatch)

        # Set GitLab CI environment
        monkeypatch.setenv("GITLAB_CI", "true")
        monkeypatch.setenv("CI_PROJECT_PATH", "group/project")

        config = Config(
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )

        assert config.platform_provider == PlatformProvider.GITLAB

    def test_config_platform_autodetection_github_actions(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test platform auto-detection for GitHub Actions."""
        clear_config_env_vars(monkeypatch)

        # Set GitHub Actions environment
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

        config = Config(
            github_token="ghp_test",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )

        assert config.platform_provider == PlatformProvider.GITHUB

    def test_config_platform_autodetection_github_repository_only(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test platform auto-detection with GITHUB_REPOSITORY only (fallback detection)."""
        clear_config_env_vars(monkeypatch)

        # Set only GitHub repository (fallback case - data available but no explicit CI flag)
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

        config = Config(
            github_token="ghp_test",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )

        assert config.platform_provider == PlatformProvider.GITHUB

    def test_config_platform_explicit_override(self, monkeypatch: MonkeyPatch) -> None:
        """Test that explicit platform specification overrides auto-detection."""
        clear_config_env_vars(monkeypatch)

        # Set GitHub environment but force GitLab
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

        config = Config(
            platform_provider=PlatformProvider.GITLAB,  # Explicit override
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )

        assert config.platform_provider == PlatformProvider.GITLAB

    def test_config_platform_autodetection_fallback(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test platform auto-detection falls back to GitLab when no CI detected."""
        clear_config_env_vars(monkeypatch)

        # No CI environment variables set
        config = Config(
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )

        assert config.platform_provider == PlatformProvider.GITLAB

    def test_config_platform_autodetection_dirty_environment(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test platform auto-detection handles dirty environments safely."""
        clear_config_env_vars(monkeypatch)

        # Dirty environment: CI flag but no data (should fallback to default)
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        # NO GITHUB_REPOSITORY - dirty environment

        config = Config(
            gitlab_token="test",  # Provide GitLab token for fallback
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )

        # Should fallback to GitLab since no usable GitHub data
        assert config.platform_provider == PlatformProvider.GITLAB

    def test_config_effective_values_fallback(self, monkeypatch: MonkeyPatch) -> None:
        """Test fallback to regular values when CI vars not available."""
        # Clear all CI environment variables to ensure clean test
        ci_vars_to_clear = [
            "CI_PROJECT_PATH",
            "CI_MERGE_REQUEST_IID",
            "CI_SERVER_URL",
            "GITLAB_CI",
            "GITHUB_REPOSITORY",  # Clear GitHub vars too
            "GITHUB_SERVER_URL",
        ]
        for var in ci_vars_to_clear:
            monkeypatch.delenv(var, raising=False)

        config = Config(
            gitlab_token="test",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirement
            ai_model="qwen2.5-coder:7b",  # Specify appropriate model for Ollama
            gitlab_url="https://gitlab.com",
        )

        # Should return None for project/MR (no CI vars)
        assert config.get_effective_project_id() is None
        assert config.get_effective_mr_iid() is None
        # Should fallback to regular gitlab_url
        assert config.get_effective_gitlab_url() == "https://gitlab.com"

    def test_model_provider_compatibility_validation(self) -> None:
        """Test model/provider compatibility validation."""
        # Valid combinations should work
        config_ollama = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        assert config_ollama.ai_provider == AIProvider.OLLAMA
        assert config_ollama.ai_model == "qwen2.5-coder:7b"

        config_gemini = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.GEMINI,
            ai_model="gemini-2.5-pro",
            ai_api_key="test_key",
        )
        assert config_gemini.ai_provider == AIProvider.GEMINI
        assert config_gemini.ai_model == "gemini-2.5-pro"

        # Invalid combinations should raise ValueError
        with pytest.raises(
            ValueError, match="appears to be for a cloud provider.*Ollama"
        ):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ai_model="gemini-2.5-pro",  # Wrong model for Ollama
            )

        with pytest.raises(ValueError, match="is not a valid Gemini model"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.GEMINI,
                ai_model="qwen2.5-coder:7b",  # Wrong model for Gemini
                ai_api_key="test_key",
            )

        # Obsolete Gemini models should also be rejected
        with pytest.raises(ValueError, match="is not a valid Gemini model"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.GEMINI,
                ai_model="gemini-pro",  # Obsolete model
                ai_api_key="test_key",
            )

        with pytest.raises(ValueError, match="is not a valid Gemini model"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.GEMINI,
                ai_model="gemini-pro-vision",  # Obsolete model
                ai_api_key="test_key",
            )

    def test_ssl_configuration_defaults(self, monkeypatch: MonkeyPatch) -> None:
        """Test SSL configuration defaults."""
        clear_config_env_vars(monkeypatch)

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )

        assert config.ssl_verify is True
        assert config.ssl_cert_path is None

    def test_ssl_configuration_custom_values(self, monkeypatch: MonkeyPatch) -> None:
        """Test SSL configuration with custom values."""
        clear_config_env_vars(monkeypatch)

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            ssl_verify=False,
        )

        assert config.ssl_verify is False
        assert config.ssl_cert_path is None

    def test_ssl_cert_path_validation_nonexistent_file(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test SSL cert path validation with non-existent file."""
        clear_config_env_vars(monkeypatch)

        with pytest.raises(ValueError, match="SSL certificate file not found"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ai_model="qwen2.5-coder:7b",
                ssl_cert_path="/path/to/nonexistent/cert.pem",
            )

    def test_ssl_cert_path_validation_empty_path(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test SSL cert path validation with empty path."""
        clear_config_env_vars(monkeypatch)

        with pytest.raises(ValueError, match="SSL certificate path cannot be empty"):
            Config(
                gitlab_token="test_token",
                ai_provider=AIProvider.OLLAMA,
                ai_model="qwen2.5-coder:7b",
                ssl_cert_path="",
            )

    def test_ssl_cert_path_validation_valid_file(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test SSL cert path validation with valid file."""
        clear_config_env_vars(monkeypatch)

        # Create a temporary certificate file
        cert_file = tmp_path / "test_cert.pem"
        cert_file.write_text(
            "-----BEGIN CERTIFICATE-----\nMockCertificateContent\n-----END CERTIFICATE-----\n"
        )

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            ssl_cert_path=str(cert_file),
        )

        assert config.ssl_verify is True  # default
        assert config.ssl_cert_path == str(cert_file)

    def test_auto_model_assignment_gemini_default(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test that Gemini model is assigned automatically when no provider/model specified."""
        clear_config_env_vars(monkeypatch)

        # Gemini is a cloud provider, so it needs an API key
        config = Config(gitlab_token="test_token", ai_api_key="test_api_key")

        # Should default to Gemini provider and auto-assign model through get_ai_model()
        from ai_code_review.models.config import _DEFAULT_MODELS

        assert config.ai_provider == AIProvider.GEMINI
        assert config.ai_model is None  # Field is None
        assert (
            config.get_ai_model() == _DEFAULT_MODELS[AIProvider.GEMINI]
        )  # Getter returns default

    def test_auto_model_assignment_explicit_provider(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test that model is assigned automatically for explicitly specified provider."""
        clear_config_env_vars(monkeypatch)

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.ANTHROPIC,
            ai_api_key="test_key",
        )

        # Should auto-assign model for Anthropic through get_ai_model()
        assert config.ai_provider == AIProvider.ANTHROPIC
        assert config.get_ai_model() == "claude-sonnet-4-20250514"

    def test_enable_project_context_defaults_true(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test that enable_project_context defaults to True."""
        clear_config_env_vars(monkeypatch)

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        assert config.enable_project_context is True

    def test_enable_project_context_can_be_disabled(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test that enable_project_context can be disabled."""
        clear_config_env_vars(monkeypatch)

        # Via constructor
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            enable_project_context=False,
        )
        assert config.enable_project_context is False

        # Via environment variable
        monkeypatch.setenv("ENABLE_PROJECT_CONTEXT", "false")
        config2 = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        assert config2.enable_project_context is False

    def test_project_context_file_defaults_correctly(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test that project_context_file has correct default value."""
        clear_config_env_vars(monkeypatch)

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        assert config.project_context_file == ".ai_review/project.md"

    def test_project_context_file_can_be_customized(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test that project_context_file can be customized."""
        clear_config_env_vars(monkeypatch)

        # Via constructor
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            project_context_file="custom/path/context.md",
        )
        assert config.project_context_file == "custom/path/context.md"

        # Via environment variable
        monkeypatch.setenv("PROJECT_CONTEXT_FILE", "env/context.md")
        config2 = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
        )
        assert config2.project_context_file == "env/context.md"


class TestPlatformModels:
    """Test platform-agnostic data models."""

    def test_pull_request_diff(self) -> None:
        """Test PullRequestDiff model."""
        diff = PullRequestDiff(
            file_path="src/test.py", diff="@@ -1,3 +1,3 @@\n-old line\n+new line"
        )

        assert diff.file_path == "src/test.py"
        assert diff.new_file is False
        assert diff.renamed_file is False
        assert diff.deleted_file is False

    def test_pull_request_info(self) -> None:
        """Test PullRequestInfo model."""
        info = PullRequestInfo(
            id=123,
            number=456,
            title="Test MR",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="opened",
            web_url="https://gitlab.com/test/test/-/merge_requests/456",
        )

        assert info.id == 123
        assert info.number == 456
        assert info.description is None

    def test_pull_request_data_properties(self) -> None:
        """Test PullRequestData calculated properties."""
        diffs = [
            PullRequestDiff(file_path="file1.py", diff="short diff"),
            PullRequestDiff(file_path="file2.py", diff="longer diff content"),
        ]

        info = PullRequestInfo(
            id=123,
            number=456,
            title="Test",
            source_branch="feature",
            target_branch="main",
            author="user",
            state="opened",
            web_url="https://gitlab.com/test/-/merge_requests/456",
        )

        commits = [
            PullRequestCommit(
                id="abc123",
                title="Test commit",
                message="Test commit message",
                author_name="Test Author",
                author_email="test@example.com",
                committed_date="2024-01-01T12:00:00Z",
                short_id="abc123",
            )
        ]

        pr_data = PullRequestData(info=info, diffs=diffs, commits=commits)

        assert pr_data.file_count == 2
        assert pr_data.total_chars == len("short diff") + len("longer diff content")
        assert pr_data.commit_count == 1


class TestReviewModels:
    """Test review data models."""

    def test_review_result_to_markdown(self) -> None:
        """Test converting ReviewResult to markdown format (MVP simplified version)."""
        # Create a simple review
        file_review = FileReview(
            file_path="test.py", summary="Test review", comments=[]
        )

        review = CodeReview(
            general_feedback="### General Feedback\n\nGood code overall\n\n### ✅ Summary\n- Overall good quality",
            file_reviews=[file_review],
            overall_assessment="Looks good",
            priority_issues=["Fix issue X"],
            minor_suggestions=["Minor fix Y"],
        )

        result = ReviewResult(review=review)
        markdown = result.to_markdown()

        # Test that we get the AI-generated content directly
        assert "Good code overall" in markdown
        assert "General Feedback" in markdown
        assert "Overall good quality" in markdown


class TestGetDefaultModelForProvider:
    """Test the get_default_model_for_provider function."""

    def test_get_default_model_for_all_providers(self) -> None:
        """Test that all AIProvider enum values have default models."""
        # Test each provider has a default model (use the constants)
        from ai_code_review.models.config import (
            _DEFAULT_MODELS,
            AIProvider,
            get_default_model_for_provider,
        )

        assert (
            get_default_model_for_provider(AIProvider.OLLAMA)
            == _DEFAULT_MODELS[AIProvider.OLLAMA]
        )
        assert (
            get_default_model_for_provider(AIProvider.GEMINI)
            == _DEFAULT_MODELS[AIProvider.GEMINI]
        )
        assert (
            get_default_model_for_provider(AIProvider.ANTHROPIC)
            == _DEFAULT_MODELS[AIProvider.ANTHROPIC]
        )
        assert (
            get_default_model_for_provider(AIProvider.OPENAI)
            == _DEFAULT_MODELS[AIProvider.OPENAI]
        )

        # Ensure all enum members are covered (no missing providers)
        all_providers = set(AIProvider)
        tested_providers = {
            AIProvider.OLLAMA,
            AIProvider.GEMINI,
            AIProvider.ANTHROPIC,
            AIProvider.OPENAI,
        }
        assert all_providers == tested_providers, (
            f"Missing tests for providers: {all_providers - tested_providers}"
        )

    def test_get_default_model_fails_for_undefined_provider(self) -> None:
        """Test that function fails explicitly for undefined providers (future-proofing)."""
        from unittest.mock import patch

        from ai_code_review.models.config import (
            get_default_model_for_provider,
        )

        # Create a mock provider that's not in the defaults
        with patch("ai_code_review.models.config.AIProvider"):
            # Create a fake provider instance that's not in defaults
            fake_provider = type("MockProvider", (), {"value": "fake_provider"})()
            fake_provider.value = "fake_provider"

            with pytest.raises(
                ValueError,
                match="No default model defined for provider 'fake_provider'",
            ):
                get_default_model_for_provider(fake_provider)  # type: ignore
