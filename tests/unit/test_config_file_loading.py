"""Unit tests for YAML configuration file loading functionality."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ai_code_review.models.config import AIProvider, Config, PlatformProvider


def clean_test_env_vars() -> dict[str, str]:
    """Clean environment variables for test isolation.

    Returns:
        dict: Safe test environment variables
    """
    return {
        # Provide minimal safe values for authentication to avoid validation errors
        "AI_API_KEY": "fake_test_api_key",
        "GITLAB_TOKEN": "fake_test_token",
        "GITHUB_TOKEN": "fake_test_token",
        # Silence GitPython in CI environments
        "GIT_PYTHON_REFRESH": "quiet",
    }


class TestConfigFileLoading:
    """Test YAML configuration file loading functionality."""

    def test_auto_detection_config_file_loads(self, tmp_path: Path) -> None:
        """Test auto-detection of .ai_review/config.yml file."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Setup: Create .ai_review/config.yml
            config_dir = tmp_path / ".ai_review"
            config_dir.mkdir()
            config_file = config_dir / "config.yml"

            config_data = {
                "ai_provider": "ollama",
                "ai_model": "qwen2.5-coder:7b",
                "platform_provider": "gitlab",  # Use gitlab instead of local (no git repo required)
                "log_level": "DEBUG",
            }
            config_file.write_text(yaml.dump(config_data))

            # Change to temp directory to test auto-detection
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                config = Config.from_cli_args({})

                assert config.ai_provider == AIProvider.OLLAMA
                assert config.ai_model == "qwen2.5-coder:7b"
                assert config.platform_provider == PlatformProvider.GITLAB
                assert config.log_level == "DEBUG"
            finally:
                os.chdir(original_cwd)

    def test_custom_config_file_path(self, tmp_path: Path) -> None:
        """Test --config-file option with custom path."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Setup: Create custom config file
            custom_config = tmp_path / "custom-config.yml"
            config_data = {
                "ai_provider": "anthropic",
                "ai_model": "claude-3-5-sonnet-20241022",
                "platform_provider": "github",
                "max_tokens": 4000,
            }
            custom_config.write_text(yaml.dump(config_data))

            # Test: Load custom config file
            cli_args = {
                "config_file": str(custom_config),
                "local": True,  # Override from CLI should take precedence
            }
            config = Config.from_cli_args(cli_args)

            # Config file values
            assert config.ai_provider == AIProvider.ANTHROPIC
            assert config.ai_model == "claude-3-5-sonnet-20241022"
            assert config.max_tokens == 4000
            # CLI override should win
            assert config.platform_provider == PlatformProvider.LOCAL

    def test_no_config_file_flag_skips_loading(self, tmp_path: Path) -> None:
        """Test --no-config-file flag skips config file loading."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Setup: Create config file that should be ignored
            config_dir = tmp_path / ".ai_review"
            config_dir.mkdir()
            config_file = config_dir / "config.yml"
            config_data = {"ai_provider": "ollama", "log_level": "DEBUG"}
            config_file.write_text(yaml.dump(config_data))

            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                # Test: --no-config-file should ignore the file
                cli_args = {
                    "no_config_file": True,
                    "provider": "anthropic",
                    "platform": "gitlab",  # Use gitlab instead of local flag
                }
                config = Config.from_cli_args(cli_args)

                # Should use CLI/default values, NOT config file
                assert config.ai_provider == AIProvider.ANTHROPIC  # From CLI
                assert config.platform_provider == PlatformProvider.GITLAB  # From CLI
                assert config.log_level == "INFO"  # Default, not DEBUG from file
            finally:
                os.chdir(original_cwd)

    def test_nonexistent_autodetect_config_ignored(self, tmp_path: Path) -> None:
        """Test non-existent auto-detected config file is silently ignored."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Change to temp directory without .ai_review/config.yml
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)  # Directory without config file
                cli_args = {
                    "provider": "ollama",
                    "platform": "gitlab",
                }

                # Should not raise error, should use defaults/CLI (auto-detection finds nothing)
                config = Config.from_cli_args(cli_args)
                assert config.ai_provider == AIProvider.OLLAMA
                assert config.platform_provider == PlatformProvider.GITLAB
            finally:
                os.chdir(original_cwd)

    def test_explicit_nonexistent_config_file_raises_error(self) -> None:
        """Test explicitly specified non-existent config file raises ValueError."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            cli_args = {
                "config_file": "/path/that/does/not/exist.yml",
                "provider": "ollama",
                "platform": "gitlab",
            }

            # Should raise error because config file was explicitly specified
            with pytest.raises(ValueError) as exc_info:
                Config.from_cli_args(cli_args)

            assert "Config file not found" in str(exc_info.value)
            assert "/path/that/does/not/exist.yml" in str(exc_info.value)
            assert "Please check the path or remove --config-file" in str(
                exc_info.value
            )

    def test_yaml_syntax_error_handling(self, tmp_path: Path) -> None:
        """Test descriptive error for invalid YAML syntax."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Setup: Create invalid YAML file
            invalid_config = tmp_path / "invalid.yml"
            invalid_config.write_text("ai_provider: [unclosed array")

            cli_args = {"config_file": str(invalid_config), "local": True}

            with pytest.raises(ValueError) as exc_info:
                Config.from_cli_args(cli_args)

            assert "Invalid YAML syntax in config file" in str(exc_info.value)
            assert str(invalid_config) in str(exc_info.value)

    def test_file_permission_error_handling(self, tmp_path: Path) -> None:
        """Test descriptive error for file permission issues."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Setup: Create config file
            protected_config = tmp_path / "protected.yml"
            protected_config.write_text("ai_provider: ollama")

            cli_args = {"config_file": str(protected_config), "local": True}

            # Mock open() to simulate permission error (root can read 0o000 files in CI)
            with patch(
                "builtins.open", side_effect=PermissionError("Permission denied")
            ):
                with pytest.raises(ValueError) as exc_info:
                    Config.from_cli_args(cli_args)

                assert "Failed to read config file" in str(exc_info.value)
                assert str(protected_config) in str(exc_info.value)

    def test_invalid_yaml_content_error(self, tmp_path: Path) -> None:
        """Test error when YAML content is not a dictionary."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Setup: Valid YAML but not an object
            invalid_content_config = tmp_path / "not-dict.yml"
            invalid_content_config.write_text("- this\n- is\n- a\n- list")

            cli_args = {"config_file": str(invalid_content_config), "local": True}

            with pytest.raises(ValueError) as exc_info:
                Config.from_cli_args(cli_args)

            assert "Config file must contain a YAML object, got list" in str(
                exc_info.value
            )

    def test_priority_order_cli_over_config_file(self, tmp_path: Path) -> None:
        """Test CLI arguments have higher priority than config file."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            # Setup: Config file with certain values
            config_file = tmp_path / "priority-test.yml"
            config_data = {
                "ai_provider": "gemini",
                "ai_model": "gemini-2.5-pro",
                "platform_provider": "gitlab",
                "max_tokens": 8000,
                "log_level": "ERROR",
            }
            config_file.write_text(yaml.dump(config_data))

            # Test: CLI args should override config file
            cli_args = {
                "config_file": str(config_file),
                "provider": "anthropic",  # Should override gemini
                "model": "claude-3-5-sonnet-20241022",  # Should override gemini model
                "local": True,  # Should override gitlab platform
                "log_level": "DEBUG",  # Should override ERROR
                # max_tokens not specified, should come from config file
            }

            config = Config.from_cli_args(cli_args)

            # CLI overrides
            assert config.ai_provider == AIProvider.ANTHROPIC
            assert config.ai_model == "claude-3-5-sonnet-20241022"
            assert config.platform_provider == PlatformProvider.LOCAL
            assert config.log_level == "DEBUG"

            # Config file value (not overridden)
            assert config.max_tokens == 8000


class TestLayeredConfiguration:
    """Test from_layered_config method specifically."""

    def test_empty_config_file_data(self) -> None:
        """Test layered config with empty config file data."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            cli_data = {"ai_provider": "ollama", "platform_provider": "local"}
            config_file_data = {}

            config = Config.from_layered_config(cli_data, config_file_data)

            assert config.ai_provider == AIProvider.OLLAMA
            assert config.platform_provider == PlatformProvider.LOCAL

    def test_config_file_only_data(self) -> None:
        """Test layered config with only config file data."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            cli_data = {}
            config_file_data = {
                "ai_provider": "anthropic",
                "ai_model": "claude-3-5-sonnet-20241022",
                "log_level": "WARNING",
            }

            config = Config.from_layered_config(cli_data, config_file_data)

            assert config.ai_provider == AIProvider.ANTHROPIC
            assert config.ai_model == "claude-3-5-sonnet-20241022"
            assert config.log_level == "WARNING"

    def test_cli_overrides_config_file_layering(self) -> None:
        """Test CLI data overrides config file data in layered config."""
        with patch.dict("os.environ", clean_test_env_vars(), clear=True):
            cli_data = {
                "ai_provider": "anthropic",  # Override to anthropic
                "ai_model": "claude-3-5-sonnet-20241022",  # Explicit model to keep
                "platform_provider": "local",
                "max_tokens": 12000,
            }
            config_file_data = {
                "ai_provider": "gemini",  # Should be overridden
                "ai_model": "gemini-2.5-pro",  # Should be overridden by explicit CLI model
                "platform_provider": "gitlab",  # Should be overridden
                "max_tokens": 8000,  # Should be overridden
                "log_level": "DEBUG",  # Should be kept
            }

            config = Config.from_layered_config(cli_data, config_file_data)

            # CLI wins
            assert config.ai_provider == AIProvider.ANTHROPIC
            assert config.platform_provider == PlatformProvider.LOCAL
            assert config.max_tokens == 12000
            assert (
                config.ai_model == "claude-3-5-sonnet-20241022"
            )  # Explicit CLI model kept

            # Config file values kept when no CLI override
            assert config.log_level == "DEBUG"
