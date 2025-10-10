"""Unit tests for Config class."""

from __future__ import annotations

from unittest.mock import patch

from ai_code_review.models.config import (
    _DEFAULT_EXCLUDE_PATTERNS,
    AIProvider,
    Config,
    PlatformProvider,
)


class TestConfigFromCliArgs:
    """Test Config.from_cli_args method with specific mapping scenarios."""

    def test_local_flag_mapping(self) -> None:
        """Test --local flag correctly sets platform_provider to LOCAL."""
        cli_args = {
            "local": True,
            "dry_run": True,
            "provider": "ollama",
        }

        config = Config.from_cli_args(cli_args)

        assert config.platform_provider == PlatformProvider.LOCAL
        assert config.ai_provider == AIProvider.OLLAMA

    def test_no_file_filtering_mapping(self) -> None:
        """Test --no-file-filtering correctly results in empty exclude_patterns."""
        cli_args = {
            "no_file_filtering": True,
            "local": True,
            "provider": "ollama",
        }

        config = Config.from_cli_args(cli_args)

        assert config.exclude_patterns == []

    def test_exclude_files_mapping(self) -> None:
        """Test --exclude-files correctly appends to default patterns."""
        cli_args = {
            "exclude_files": ("custom.txt", "another.log"),
            "local": True,
            "provider": "ollama",
        }

        config = Config.from_cli_args(cli_args)

        expected_patterns = _DEFAULT_EXCLUDE_PATTERNS + ["custom.txt", "another.log"]
        assert config.exclude_patterns == expected_patterns

    def test_provider_without_model_sets_default(self) -> None:
        """Test --provider ollama without --model sets default Ollama model."""
        cli_args = {
            "provider": "ollama",
            "local": True,
        }

        config = Config.from_cli_args(cli_args)

        assert config.ai_provider == AIProvider.OLLAMA
        assert config.ai_model == "qwen2.5-coder:7b"  # Default Ollama model

    def test_provider_with_model_overrides_default(self) -> None:
        """Test --provider and --model both specified uses custom model."""
        cli_args = {
            "provider": "ollama",
            "model": "custom-model",
            "local": True,
        }

        config = Config.from_cli_args(cli_args)

        assert config.ai_provider == AIProvider.OLLAMA
        assert config.ai_model == "custom-model"

    def test_no_mr_summary_flag_mapping(self) -> None:
        """Test --no-mr-summary correctly sets include_mr_summary to False."""
        cli_args = {
            "no_mr_summary": True,
            "local": True,
            "provider": "ollama",
        }

        config = Config.from_cli_args(cli_args)

        assert config.include_mr_summary is False

    def test_direct_mappings(self) -> None:
        """Test fields with direct CLI name to config field mapping."""
        cli_args = {
            "post": True,
            "output_file": "/tmp/output.txt",
            "health_check": True,
            "local": True,
            "provider": "ollama",
        }

        config = Config.from_cli_args(cli_args)

        assert config.post is True
        assert config.output_file == "/tmp/output.txt"
        assert config.health_check is True

    def test_cli_to_config_map_mappings(self) -> None:
        """Test CLI_TO_CONFIG_MAP mappings work correctly."""
        cli_args = {
            "provider": "ollama",  # maps to ai_provider (no auth required)
            "model": "custom-model",  # maps to ai_model
            "ollama_url": "http://custom:11434",  # maps to ollama_base_url
            "local": True,  # maps to local platform (no auth required)
            "project_context": True,  # maps to enable_project_context
            "context_file": "context.txt",  # maps to project_context_file
        }

        config = Config.from_cli_args(cli_args)

        assert config.ai_provider == AIProvider.OLLAMA
        assert config.ai_model == "custom-model"
        assert config.ollama_base_url == "http://custom:11434"
        assert config.platform_provider == PlatformProvider.LOCAL
        assert config.enable_project_context is True
        assert config.project_context_file == "context.txt"

    def test_enum_conversion(self) -> None:
        """Test string CLI args are properly converted to enums."""
        cli_args = {
            "provider": "ollama",  # string -> AIProvider (no auth required)
            "local": True,  # local platform (no auth required)
        }

        config = Config.from_cli_args(cli_args)

        assert config.ai_provider == AIProvider.OLLAMA
        assert config.platform_provider == PlatformProvider.LOCAL
        assert isinstance(config.ai_provider, AIProvider)
        assert isinstance(config.platform_provider, PlatformProvider)

    def test_special_case_precedence(self) -> None:
        """Test special cases override mapped values correctly."""
        cli_args = {
            "platform": "github",  # Would normally map to platform_provider
            "local": True,  # But --local should override to LOCAL
            "provider": "ollama",
        }

        config = Config.from_cli_args(cli_args)

        # local flag should take precedence
        assert config.platform_provider == PlatformProvider.LOCAL

    def test_empty_cli_args(self) -> None:
        """Test empty CLI args uses all defaults."""
        cli_args: dict[str, any] = {}

        # Provide fake env vars to satisfy validation for default providers
        with patch.dict(
            "os.environ",
            {
                "AI_API_KEY": "fake_api_key_for_testing",
                "GITLAB_TOKEN": "fake_gitlab_token",
            },
        ):
            config = Config.from_cli_args(cli_args)

            # Should use defaults
            assert config.platform_provider == PlatformProvider.GITLAB
            assert config.ai_provider == AIProvider.GEMINI
            assert config.exclude_patterns == _DEFAULT_EXCLUDE_PATTERNS
            assert config.include_mr_summary is True
