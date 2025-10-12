"""Shared utility functions for context generator sections."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic_settings import BaseSettings

T = TypeVar("T", bound=BaseSettings)


def extract_ci_system(facts: dict[str, Any]) -> str | None:
    """Extract CI/CD system from tech indicators.

    Args:
        facts: Project facts containing tech indicators

    Returns:
        CI system name (gitlab-ci, github-actions, etc.) or None if not found
    """
    tech_indicators = facts.get("tech_indicators", {})
    ci_systems = tech_indicators.get("ci_cd", [])

    # Return first detected CI system (usually only one)
    if ci_systems and isinstance(ci_systems, list) and len(ci_systems) > 0:
        return str(ci_systems[0])

    return None


def load_feature_config[T: BaseSettings](
    model_cls: type[T],
    yaml_config: dict[str, Any],
    config_key: str,
    cli_overrides: dict[str, Any] | None = None,
) -> T:
    """Load feature configuration with proper precedence.

    Args:
        model_cls: The Pydantic BaseSettings model class
        yaml_config: YAML configuration data
        config_key: Key to extract from YAML config
        cli_overrides: CLI overrides to apply (highest precedence)

    Returns:
        Configured model instance

    Configuration precedence (highest to lowest):
    1. CLI arguments (cli_overrides)
    2. YAML configuration file (yaml_config)
    3. Environment variables (handled by BaseSettings)
    4. Field defaults
    """
    # Start with environment variables (BaseSettings default behavior)
    config = model_cls()

    # Override with YAML data if present
    yaml_data = yaml_config.get(config_key, {})
    if yaml_data:
        for key, value in yaml_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

    # Override with CLI arguments (highest precedence)
    if cli_overrides:
        for key, value in cli_overrides.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

    return config
