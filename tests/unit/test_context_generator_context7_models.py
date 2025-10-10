"""Tests for Context7 models and configuration."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from context_generator.models import Context7Config


class TestContext7Config:
    """Test Context7Config model."""

    def test_init_defaults(self) -> None:
        """Test Context7Config initialization with defaults."""
        config = Context7Config()

        assert config.enabled is False
        assert config.max_tokens_per_library == 2000
        assert config.priority_libraries == []
        assert config.timeout_seconds == 10

    def test_init_with_values(self) -> None:
        """Test Context7Config initialization with custom values."""
        config = Context7Config(
            enabled=True,
            max_tokens_per_library=1500,
            priority_libraries=["fastapi", "pydantic"],
            timeout_seconds=15,
        )

        assert config.enabled is True
        assert config.max_tokens_per_library == 1500
        assert config.priority_libraries == ["fastapi", "pydantic"]
        assert config.timeout_seconds == 15

    def test_validation_max_tokens_range(self) -> None:
        """Test validation of max_tokens_per_library range."""
        # Valid values
        Context7Config(max_tokens_per_library=100)  # Minimum
        Context7Config(max_tokens_per_library=10000)  # Maximum
        Context7Config(max_tokens_per_library=2000)  # Default

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            Context7Config(max_tokens_per_library=50)  # Below minimum

        with pytest.raises(ValueError):
            Context7Config(max_tokens_per_library=15000)  # Above maximum

    def test_validation_timeout_range(self) -> None:
        """Test validation of timeout_seconds range."""
        # Valid values
        Context7Config(timeout_seconds=1)  # Minimum
        Context7Config(timeout_seconds=60)  # Maximum
        Context7Config(timeout_seconds=10)  # Default

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            Context7Config(timeout_seconds=0)  # Below minimum

        with pytest.raises(ValueError):
            Context7Config(timeout_seconds=120)  # Above maximum

    def test_from_yaml_file_nonexistent(self) -> None:
        """Test loading from non-existent YAML file returns defaults."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "nonexistent.yml"

            config = Context7Config.from_yaml_file(config_path)

            # Should return default config
            assert config.enabled is False
            assert config.max_tokens_per_library == 2000
            assert config.priority_libraries == []
            assert config.timeout_seconds == 10

    def test_from_yaml_file_auto_detect_missing(self) -> None:
        """Test auto-detection when .ai_review/config.yml doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = Path.cwd()
            try:
                # Change to temp directory where no config file exists
                import os

                os.chdir(tmp_dir)

                config = Context7Config.from_yaml_file()

                # Should return default config
                assert config.enabled is False
                assert config.max_tokens_per_library == 2000

            finally:
                os.chdir(original_cwd)

    def test_from_yaml_file_success(self) -> None:
        """Test successful loading from YAML file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yml"

            # Create test YAML file
            yaml_content = {
                "context7": {
                    "enabled": True,
                    "max_tokens_per_library": 1500,
                    "priority_libraries": ["fastapi", "pydantic", "sqlalchemy"],
                    "timeout_seconds": 15,
                }
            }

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f)

            config = Context7Config.from_yaml_file(config_path)

            assert config.enabled is True
            assert config.max_tokens_per_library == 1500
            assert config.priority_libraries == ["fastapi", "pydantic", "sqlalchemy"]
            assert config.timeout_seconds == 15

    def test_from_yaml_file_partial_config(self) -> None:
        """Test loading from YAML file with partial Context7 configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yml"

            # Create YAML file with only some Context7 settings
            yaml_content = {
                "context7": {
                    "enabled": True,
                    "priority_libraries": ["fastapi"],
                    # Missing max_tokens_per_library and timeout_seconds
                },
                "other_section": {"some_setting": "value"},
            }

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f)

            config = Context7Config.from_yaml_file(config_path)

            # Should use provided values and defaults for missing ones
            assert config.enabled is True
            assert config.priority_libraries == ["fastapi"]
            assert config.max_tokens_per_library == 2000  # Default
            assert config.timeout_seconds == 10  # Default

    def test_from_yaml_file_no_context7_section(self) -> None:
        """Test loading from YAML file without Context7 section."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yml"

            # Create YAML file without context7 section
            yaml_content = {"other_section": {"some_setting": "value"}}

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_content, f)

            config = Context7Config.from_yaml_file(config_path)

            # Should return default config
            assert config.enabled is False
            assert config.max_tokens_per_library == 2000
            assert config.priority_libraries == []
            assert config.timeout_seconds == 10

    def test_from_yaml_file_invalid_yaml(self) -> None:
        """Test loading from invalid YAML file returns defaults."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yml"

            # Create invalid YAML file
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("invalid: yaml: content: [")

            config = Context7Config.from_yaml_file(config_path)

            # Should return default config on error
            assert config.enabled is False
            assert config.max_tokens_per_library == 2000

    def test_from_yaml_file_permission_error(self) -> None:
        """Test loading from file with permission error returns defaults."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yml"

            # Create file and make it unreadable
            config_path.touch()
            config_path.chmod(0o000)

            try:
                config = Context7Config.from_yaml_file(config_path)

                # Should return default config on error
                assert config.enabled is False
                assert config.max_tokens_per_library == 2000
            finally:
                # Restore permissions for cleanup
                config_path.chmod(0o644)

    def test_from_dict_success(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "enabled": True,
            "max_tokens_per_library": 1500,
            "priority_libraries": ["fastapi", "pydantic"],
            "timeout_seconds": 15,
        }

        config = Context7Config.from_dict(data)

        assert config.enabled is True
        assert config.max_tokens_per_library == 1500
        assert config.priority_libraries == ["fastapi", "pydantic"]
        assert config.timeout_seconds == 15

    def test_from_dict_partial(self) -> None:
        """Test creating config from partial dictionary."""
        data = {"enabled": True, "priority_libraries": ["fastapi"]}

        config = Context7Config.from_dict(data)

        assert config.enabled is True
        assert config.priority_libraries == ["fastapi"]
        assert config.max_tokens_per_library == 2000  # Default
        assert config.timeout_seconds == 10  # Default

    def test_from_dict_empty(self) -> None:
        """Test creating config from empty dictionary."""
        config = Context7Config.from_dict({})

        # Should use all defaults
        assert config.enabled is False
        assert config.max_tokens_per_library == 2000
        assert config.priority_libraries == []
        assert config.timeout_seconds == 10
