"""Data models for context generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ContextResult(BaseModel):
    """Result of context generation."""

    project_path: Path
    project_name: str
    context_content: str
    generation_timestamp: str
    ai_provider: str
    ai_model: str

    @classmethod
    def create(
        cls,
        project_path: Path,
        project_name: str,
        context_content: str,
        ai_provider: str,
        ai_model: str,
    ) -> ContextResult:
        """Create a new context result."""
        return cls(
            project_path=project_path,
            project_name=project_name,
            context_content=context_content,
            generation_timestamp=datetime.now().isoformat(),
            ai_provider=ai_provider,
            ai_model=ai_model,
        )


class Context7Config(BaseSettings):
    """Configuration for Context7 integration."""

    enabled: bool = Field(
        default=False, description="Enable Context7 documentation fetching"
    )
    api_key: str | None = Field(
        default=None, description="Context7 API key", alias="CONTEXT7_API_KEY"
    )
    max_libraries: int = Field(
        default=3, description="Maximum number of libraries to fetch documentation for"
    )
    max_tokens_per_library: int = Field(
        default=2000,
        description="Maximum tokens to fetch per library",
        ge=100,
        le=10000,
    )
    priority_libraries: list[str] = Field(
        default_factory=list,
        description="List of priority libraries to fetch documentation for",
    )
    timeout_seconds: int = Field(
        default=10, description="Timeout for Context7 API calls in seconds", ge=1, le=60
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",  # No prefix to read CONTEXT7_API_KEY directly
        "extra": "ignore",  # Ignore unknown environment variables
    }

    @classmethod
    def from_yaml_file(cls, config_path: Path | None = None) -> Context7Config:
        """Load Context7 configuration from YAML file.

        Args:
            config_path: Path to config file. If None, auto-detects .ai_review/config.yml

        Returns:
            Context7Config instance with loaded settings
        """
        # Auto-detect config file if not specified
        if config_path is None:
            config_path = Path(".ai_review/config.yml")
            if not config_path.exists():
                # Return default config (BaseSettings will load from environment automatically)
                return cls()

        # Load YAML file
        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Extract context7 section
            context7_data = data.get("context7", {})

            # Create config with extracted data (BaseSettings will merge with environment)
            return cls(**context7_data)

        except (OSError, yaml.YAMLError) as e:
            # Return default config on any error
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning(
                "Failed to load Context7 config from YAML",
                error=str(e),
                path=config_path,
            )
            return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Context7Config:
        """Create Context7Config from dictionary data.

        Args:
            data: Dictionary with Context7 configuration

        Returns:
            Context7Config instance
        """
        return cls(**data)
