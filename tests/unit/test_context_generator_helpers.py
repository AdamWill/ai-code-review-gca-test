"""Tests for context generator helper functions."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

from context_generator.utils.helpers import extract_ci_system, load_feature_config


class TestExtractCISystem:
    """Test extract_ci_system function."""

    def test_extract_ci_system_gitlab_ci(self) -> None:
        """Test extracting GitLab CI system."""
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci"]}}
        result = extract_ci_system(facts)
        assert result == "gitlab-ci"

    def test_extract_ci_system_github_actions(self) -> None:
        """Test extracting GitHub Actions system."""
        facts = {"tech_indicators": {"ci_cd": ["github-actions"]}}
        result = extract_ci_system(facts)
        assert result == "github-actions"

    def test_extract_ci_system_multiple_systems(self) -> None:
        """Test extracting first CI system when multiple are present."""
        facts = {"tech_indicators": {"ci_cd": ["gitlab-ci", "github-actions"]}}
        result = extract_ci_system(facts)
        assert result == "gitlab-ci"

    def test_extract_ci_system_no_tech_indicators(self) -> None:
        """Test when tech_indicators is missing."""
        facts = {}
        result = extract_ci_system(facts)
        assert result is None

    def test_extract_ci_system_no_ci_cd(self) -> None:
        """Test when ci_cd is missing from tech_indicators."""
        facts = {"tech_indicators": {"other": "value"}}
        result = extract_ci_system(facts)
        assert result is None

    def test_extract_ci_system_empty_list(self) -> None:
        """Test when ci_cd is an empty list."""
        facts = {"tech_indicators": {"ci_cd": []}}
        result = extract_ci_system(facts)
        assert result is None

    def test_extract_ci_system_non_list(self) -> None:
        """Test when ci_cd is not a list."""
        facts = {"tech_indicators": {"ci_cd": "gitlab-ci"}}
        result = extract_ci_system(facts)
        assert result is None


class MockConfig(BaseSettings):
    """Mock configuration model for load_feature_config tests."""

    enabled: bool = Field(default=False, description="Enable feature")
    timeout: int = Field(default=30, description="Timeout in seconds")
    max_items: int = Field(default=100, description="Maximum items")
    api_key: str = Field(default="", description="API key")


class TestLoadFeatureConfig:
    """Test load_feature_config function."""

    def test_load_feature_config_defaults_only(self) -> None:
        """Test loading with only default values."""
        yaml_config = {}
        cli_overrides = None

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is False
        assert config.timeout == 30
        assert config.max_items == 100
        assert config.api_key == ""

    def test_load_feature_config_yaml_only(self) -> None:
        """Test loading with YAML configuration only."""
        yaml_config = {"test": {"enabled": True, "timeout": 60, "max_items": 200}}
        cli_overrides = None

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is True
        assert config.timeout == 60
        assert config.max_items == 200
        assert config.api_key == ""  # Default value

    def test_load_feature_config_cli_overrides_only(self) -> None:
        """Test loading with CLI overrides only."""
        yaml_config = {}
        cli_overrides = {"enabled": True, "timeout": 45, "api_key": "test-key"}

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is True
        assert config.timeout == 45
        assert config.max_items == 100  # Default value
        assert config.api_key == "test-key"

    def test_load_feature_config_yaml_and_cli_precedence(self) -> None:
        """Test that CLI overrides take precedence over YAML."""
        yaml_config = {
            "test": {
                "enabled": True,
                "timeout": 60,
                "max_items": 200,
                "api_key": "yaml-key",
            }
        }
        cli_overrides = {"enabled": False, "timeout": 45, "api_key": "cli-key"}

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        # CLI should override YAML
        assert config.enabled is False  # CLI override
        assert config.timeout == 45  # CLI override
        assert config.max_items == 200  # YAML value (no CLI override)
        assert config.api_key == "cli-key"  # CLI override

    def test_load_feature_config_partial_yaml(self) -> None:
        """Test loading with partial YAML configuration."""
        yaml_config = {
            "test": {
                "enabled": True,
                # timeout and max_items missing
                "api_key": "yaml-key",
            }
        }
        cli_overrides = None

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is True  # From YAML
        assert config.timeout == 30  # Default value
        assert config.max_items == 100  # Default value
        assert config.api_key == "yaml-key"  # From YAML

    def test_load_feature_config_partial_cli_overrides(self) -> None:
        """Test loading with partial CLI overrides."""
        yaml_config = {
            "test": {
                "enabled": True,
                "timeout": 60,
                "max_items": 200,
                "api_key": "yaml-key",
            }
        }
        cli_overrides = {
            "enabled": False,
            # timeout, max_items, api_key missing
        }

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is False  # CLI override
        assert config.timeout == 60  # YAML value (no CLI override)
        assert config.max_items == 200  # YAML value (no CLI override)
        assert config.api_key == "yaml-key"  # YAML value (no CLI override)

    def test_load_feature_config_none_cli_overrides(self) -> None:
        """Test that None CLI overrides are ignored."""
        yaml_config = {"test": {"enabled": True, "timeout": 60}}
        cli_overrides = {
            "enabled": None,  # Should be ignored
            "timeout": 45,
        }

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is True  # YAML value (None ignored)
        assert config.timeout == 45  # CLI override
        assert config.max_items == 100  # Default value

    def test_load_feature_config_missing_yaml_section(self) -> None:
        """Test loading when YAML section is missing."""
        yaml_config = {"other_section": {"some_value": "test"}}
        cli_overrides = None

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        # Should use all default values
        assert config.enabled is False
        assert config.timeout == 30
        assert config.max_items == 100
        assert config.api_key == ""

    def test_load_feature_config_invalid_yaml_keys(self) -> None:
        """Test loading with invalid YAML keys (should be ignored)."""
        yaml_config = {
            "test": {"enabled": True, "invalid_key": "should_be_ignored", "timeout": 60}
        }
        cli_overrides = None

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is True
        assert config.timeout == 60
        assert config.max_items == 100  # Default value
        assert config.api_key == ""

    def test_load_feature_config_invalid_cli_keys(self) -> None:
        """Test loading with invalid CLI keys (should be ignored)."""
        yaml_config = {}
        cli_overrides = {
            "enabled": True,
            "invalid_key": "should_be_ignored",
            "timeout": 45,
        }

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is True
        assert config.timeout == 45
        assert config.max_items == 100  # Default value
        assert config.api_key == ""

    def test_load_feature_config_empty_yaml_section(self) -> None:
        """Test loading with empty YAML section."""
        yaml_config = {"test": {}}
        cli_overrides = None

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        # Should use all default values
        assert config.enabled is False
        assert config.timeout == 30
        assert config.max_items == 100
        assert config.api_key == ""

    def test_load_feature_config_empty_cli_overrides(self) -> None:
        """Test loading with empty CLI overrides."""
        yaml_config = {"test": {"enabled": True, "timeout": 60}}
        cli_overrides = {}

        config = load_feature_config(MockConfig, yaml_config, "test", cli_overrides)

        assert config.enabled is True  # YAML value
        assert config.timeout == 60  # YAML value
        assert config.max_items == 100  # Default value
        assert config.api_key == ""
